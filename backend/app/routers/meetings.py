import asyncio
import json
import shutil
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app import models
from app.config import get_settings
from app.database import get_db
from app.schemas import (
    DecisionRead,
    MeetingChatRequest,
    MeetingChatResponse,
    MeetingDetail,
    MeetingRead,
    MeetingSummaryRead,
    ProcessingEventRead,
    RiskRead,
    TranscriptSegmentRead,
)
from app.services.llm_provider import get_llm_provider, parse_json_object
from app.services.meeting_workflow import process_meeting, regenerate_meeting_outputs
from app.services.speaker_mapping_service import display_name_for_speaker

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


@router.post("", response_model=MeetingRead)
async def create_meeting(
    background_tasks: BackgroundTasks,
    title: str = Form(""),
    description: str | None = Form(None),
    participants: str = Form("[]"),
    enable_speaker_diarization: bool = Form(True),
    auto_process: bool = Form(True),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".mp3", ".wav", ".m4a", ".txt"}:
        raise HTTPException(status_code=400, detail="仅支持 .mp3、.wav、.m4a、.txt 文件")
    settings = get_settings()
    source_type = "text" if suffix == ".txt" else "audio"
    meeting = models.Meeting(
        title=title.strip(),
        description=description.strip() if description else None,
        source_type=source_type,
        file_path="",
        original_filename=file.filename or "meeting",
        enable_speaker_diarization=enable_speaker_diarization,
    )
    db.add(meeting)
    db.flush()
    target = settings.upload_path / f"{meeting.id}{suffix}"
    with target.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)
    meeting.file_path = str(target)
    for item in _parse_participants(participants):
        db.add(models.Participant(meeting_id=meeting.id, **item))
    db.commit()
    db.refresh(meeting)
    if auto_process:
        background_tasks.add_task(process_meeting, meeting.id)
    return meeting


@router.get("", response_model=list[MeetingRead])
def list_meetings(db: Session = Depends(get_db)):
    return db.query(models.Meeting).order_by(models.Meeting.created_at.desc()).all()


@router.get("/{meeting_id}", response_model=MeetingDetail)
def get_meeting(meeting_id: str, db: Session = Depends(get_db)):
    meeting = (
        db.query(models.Meeting)
        .options(joinedload(models.Meeting.participants))
        .filter(models.Meeting.id == meeting_id)
        .first()
    )
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    return meeting


@router.post("/{meeting_id}/chat", response_model=MeetingChatResponse)
def chat_with_meeting(meeting_id: str, payload: MeetingChatRequest, db: Session = Depends(get_db)):
    meeting = db.get(models.Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    context = _meeting_context(db, meeting_id, meeting)
    if not context.strip():
        raise HTTPException(status_code=400, detail="当前会议还没有可用于问答的内容")

    recent_history = payload.history[-8:]
    history_text = "\n".join(f"{item.role}: {item.content}" for item in recent_history)
    prompt = f"""
你是会议问答助手。只能根据【当前会议资料】回答问题，不要使用其他会议或外部知识。只输出合法 JSON：
{{"answer": "回答内容"}}
如果当前会议资料不足以回答，请直接说明“当前会议内容中没有找到相关信息”。

【当前会议资料】
{context}

【本页对话历史】
{history_text or "无"}

【用户问题】
{payload.question}
"""
    data = parse_json_object(get_llm_provider().generate(prompt), {"answer": "当前会议内容中没有找到相关信息。"})
    answer = str(data.get("answer") or "当前会议内容中没有找到相关信息。")
    return {"meeting_id": meeting_id, "answer": answer}


@router.delete("/{meeting_id}")
def delete_meeting(meeting_id: str, db: Session = Depends(get_db)):
    meeting = db.get(models.Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    db.delete(meeting)
    db.commit()
    return {"ok": True}


@router.post("/{meeting_id}/process", response_model=MeetingRead)
def start_processing(meeting_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    meeting = db.get(models.Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    background_tasks.add_task(process_meeting, meeting_id)
    return meeting


@router.post("/{meeting_id}/regenerate", response_model=MeetingRead)
def regenerate(meeting_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    meeting = db.get(models.Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    background_tasks.add_task(regenerate_meeting_outputs, meeting_id)
    return meeting


@router.get("/{meeting_id}/events")
async def meeting_events(meeting_id: str):
    async def event_stream():
        sent_ids: set[str] = set()
        while True:
            from app.database import SessionLocal

            db = SessionLocal()
            try:
                meeting = db.get(models.Meeting, meeting_id)
                if not meeting:
                    yield "event: error\ndata: {\"message\":\"meeting not found\"}\n\n"
                    break
                query = (
                    db.query(models.ProcessingEvent)
                    .filter(models.ProcessingEvent.meeting_id == meeting_id)
                    .order_by(models.ProcessingEvent.created_at)
                )
                events = query.all()
                for event in events:
                    if event.id in sent_ids:
                        continue
                    sent_ids.add(event.id)
                    payload = ProcessingEventRead.model_validate(event).model_dump_json()
                    yield f"event: processing\ndata: {payload}\n\n"
                if meeting.status in {"completed", "failed"}:
                    break
            finally:
                db.close()
            await asyncio.sleep(1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{meeting_id}/transcript", response_model=list[TranscriptSegmentRead])
def get_transcript(meeting_id: str, db: Session = Depends(get_db)):
    segments = (
        db.query(models.TranscriptSegment)
        .filter(models.TranscriptSegment.meeting_id == meeting_id)
        .order_by(models.TranscriptSegment.sequence)
        .all()
    )
    rows = []
    for segment in segments:
        display, participant_id = display_name_for_speaker(db, meeting_id, segment.speaker)
        data = TranscriptSegmentRead.model_validate(segment).model_dump()
        data["display_speaker"] = display
        data["participant_id"] = participant_id
        rows.append(data)
    return rows


@router.get("/{meeting_id}/summary", response_model=MeetingSummaryRead | None)
def get_summary(meeting_id: str, db: Session = Depends(get_db)):
    return db.query(models.MeetingSummary).filter(models.MeetingSummary.meeting_id == meeting_id).first()


@router.get("/{meeting_id}/decisions", response_model=list[DecisionRead])
def get_decisions(meeting_id: str, db: Session = Depends(get_db)):
    return db.query(models.Decision).filter(models.Decision.meeting_id == meeting_id).all()


@router.get("/{meeting_id}/risks", response_model=list[RiskRead])
def get_risks(meeting_id: str, db: Session = Depends(get_db)):
    return db.query(models.Risk).filter(models.Risk.meeting_id == meeting_id).all()


def _meeting_context(db: Session, meeting_id: str, meeting: models.Meeting) -> str:
    parts = [
        f"会议标题：{meeting.title or '未命名会议'}",
        f"会议描述：{meeting.description or meeting.original_filename}",
    ]
    segments = (
        db.query(models.TranscriptSegment)
        .filter(models.TranscriptSegment.meeting_id == meeting_id)
        .order_by(models.TranscriptSegment.sequence)
        .all()
    )
    if segments:
        lines = []
        for segment in segments:
            speaker, _participant_id = display_name_for_speaker(db, meeting_id, segment.speaker)
            lines.append(f"[{segment.start_time:.0f}-{segment.end_time:.0f}] {speaker}: {segment.content}")
        parts.append("完整转写：\n" + "\n".join(lines))

    summary = db.query(models.MeetingSummary).filter(models.MeetingSummary.meeting_id == meeting_id).first()
    if summary:
        key_points = "；".join(summary.key_points or [])
        parts.append(f"会议摘要：{summary.overview}\n关键点：{key_points}\n结论：{summary.conclusion}")

    decisions = db.query(models.Decision).filter(models.Decision.meeting_id == meeting_id).all()
    if decisions:
        parts.append("决策：\n" + "\n".join(f"- {item.content} 依据：{item.evidence or '无'}" for item in decisions))

    risks = db.query(models.Risk).filter(models.Risk.meeting_id == meeting_id).all()
    if risks:
        parts.append("风险：\n" + "\n".join(f"- {item.level} {item.risk_type}：{item.description}" for item in risks))

    actions = db.query(models.ActionItem).filter(models.ActionItem.meeting_id == meeting_id).all()
    if actions:
        parts.append("行动项：\n" + "\n".join(f"- {item.title}，负责人：{item.owner or '未指定'}，状态：{item.status}" for item in actions))

    return "\n\n".join(parts)


def _parse_participants(raw: str) -> list[dict]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    result = []
    for item in data:
        if isinstance(item, str) and item.strip():
            result.append({"name": item.strip()})
        elif isinstance(item, dict) and item.get("name"):
            result.append(
                {
                    "name": str(item["name"]).strip(),
                    "role": item.get("role"),
                    "email": item.get("email"),
                }
            )
    return result
