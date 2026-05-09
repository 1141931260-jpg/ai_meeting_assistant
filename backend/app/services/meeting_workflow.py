import re
from pathlib import Path
from typing import TypedDict

from sqlalchemy.orm import Session

from app import models
from app.database import SessionLocal
from app.services.asr_provider import TranscriptionSegment, get_asr_provider, normalize_speaker
from app.services.event_service import add_event
from app.services.extraction_service import extract_action_items, extract_decisions, extract_risks
from app.services.speaker_mapping_service import ensure_speaker_mappings
from app.services.summary_service import generate_summary
from app.services.vector_service import VectorService


class WorkflowState(TypedDict):
    meeting_id: str
    regenerate: bool


def process_meeting(meeting_id: str) -> None:
    try:
        _invoke_langgraph({"meeting_id": meeting_id, "regenerate": False})
    except Exception as exc:
        _mark_failed(meeting_id, exc)


def regenerate_meeting_outputs(meeting_id: str) -> None:
    try:
        _invoke_langgraph({"meeting_id": meeting_id, "regenerate": True})
    except Exception as exc:
        _mark_failed(meeting_id, exc)


def _invoke_langgraph(state: WorkflowState) -> None:
    try:
        from langgraph.graph import END, StateGraph
    except Exception:
        db = SessionLocal()
        try:
            _run_workflow(db, state["meeting_id"], regenerate=state["regenerate"])
        finally:
            db.close()
        return

    graph = StateGraph(WorkflowState)
    graph.add_node("load_meeting", _node_load_meeting)
    graph.add_node("load_participants", _node_load_participants)
    graph.add_node("transcribe_or_split", _node_transcribe_or_split)
    graph.add_node("generate_summary", _node_generate_summary)
    graph.add_node("extract_decisions", _node_extract_decisions)
    graph.add_node("extract_risks", _node_extract_risks)
    graph.add_node("extract_action_items", _node_extract_action_items)
    graph.add_node("build_vector_index", _node_build_vector_index)
    graph.add_node("mark_completed", _node_mark_completed)
    graph.set_entry_point("load_meeting")
    graph.add_edge("load_meeting", "load_participants")
    graph.add_edge("load_participants", "transcribe_or_split")
    graph.add_edge("transcribe_or_split", "generate_summary")
    graph.add_edge("generate_summary", "extract_decisions")
    graph.add_edge("extract_decisions", "extract_risks")
    graph.add_edge("extract_risks", "extract_action_items")
    graph.add_edge("extract_action_items", "build_vector_index")
    graph.add_edge("build_vector_index", "mark_completed")
    graph.add_edge("mark_completed", END)
    graph.compile().invoke(state)


def _with_db(fn, state: WorkflowState) -> WorkflowState:
    db = SessionLocal()
    try:
        fn(db, state)
        return state
    finally:
        db.close()


def _node_load_meeting(state: WorkflowState) -> WorkflowState:
    return _with_db(_step_load_meeting, state)


def _node_load_participants(state: WorkflowState) -> WorkflowState:
    return _with_db(lambda db, s: add_event(db, s["meeting_id"], "load_participants", "running", "读取参会人信息", 20), state)


def _node_transcribe_or_split(state: WorkflowState) -> WorkflowState:
    return _with_db(_step_transcribe_or_split, state)


def _node_generate_summary(state: WorkflowState) -> WorkflowState:
    return _with_db(lambda db, s: (add_event(db, s["meeting_id"], "generate_summary", "running", "调用 LLM API 生成摘要", 60), generate_summary(db, s["meeting_id"])), state)


def _node_extract_decisions(state: WorkflowState) -> WorkflowState:
    return _with_db(lambda db, s: (add_event(db, s["meeting_id"], "extract_decisions", "running", "提取关键决策", 66), extract_decisions(db, s["meeting_id"])), state)


def _node_extract_risks(state: WorkflowState) -> WorkflowState:
    return _with_db(lambda db, s: (add_event(db, s["meeting_id"], "extract_risks", "running", "识别风险点", 72), extract_risks(db, s["meeting_id"])), state)


def _node_extract_action_items(state: WorkflowState) -> WorkflowState:
    return _with_db(lambda db, s: (add_event(db, s["meeting_id"], "extract_action_items", "running", "提取行动项", 78), extract_action_items(db, s["meeting_id"])), state)


def _node_build_vector_index(state: WorkflowState) -> WorkflowState:
    return _with_db(lambda db, s: (add_event(db, s["meeting_id"], "build_vector_index", "running", "构建语义检索索引", 88), VectorService().build_meeting_index(db, s["meeting_id"])), state)


def _node_mark_completed(state: WorkflowState) -> WorkflowState:
    return _with_db(_step_mark_completed, state)


def _step_load_meeting(db: Session, state: WorkflowState) -> None:
    meeting = db.get(models.Meeting, state["meeting_id"])
    if not meeting:
        raise RuntimeError("会议不存在")
    meeting.status = "processing"
    meeting.error_message = None
    db.commit()
    add_event(db, state["meeting_id"], "load_meeting", "started", "会议处理已启动", 10)


def _step_transcribe_or_split(db: Session, state: WorkflowState) -> None:
    meeting = db.get(models.Meeting, state["meeting_id"])
    if not meeting:
        raise RuntimeError("会议不存在")
    if state["regenerate"]:
        add_event(db, meeting.id, "detect_speakers", "completed", "复用已有转写和 Speaker 映射", 50)
        return
    if meeting.source_type == "audio":
        add_event(db, meeting.id, "transcribe_audio", "running", "调用 ASR API 转写中", 30)
        segments = get_asr_provider().transcribe(
            meeting.file_path,
            enable_speaker_diarization=meeting.enable_speaker_diarization,
        )
    else:
        add_event(db, meeting.id, "split_transcript", "running", "解析文本会议内容", 35)
        segments = split_text_file(meeting.file_path)
    save_segments(db, meeting.id, segments)
    ensure_speaker_mappings(db, meeting.id, {segment.speaker or "Speaker 1" for segment in segments})
    add_event(db, meeting.id, "detect_speakers", "completed", "说话人标签整理完成", 50)


def _step_mark_completed(db: Session, state: WorkflowState) -> None:
    meeting = db.get(models.Meeting, state["meeting_id"])
    if meeting:
        meeting.status = "completed"
        db.commit()
    add_event(db, state["meeting_id"], "mark_completed", "completed", "处理完成", 100)


def _mark_failed(meeting_id: str, exc: Exception) -> None:
    db = SessionLocal()
    try:
        meeting = db.get(models.Meeting, meeting_id)
        if meeting:
            meeting.status = "failed"
            meeting.error_message = str(exc)
            db.commit()
        add_event(db, meeting_id, "failed", "failed", str(exc), 100)
    finally:
        db.close()


def _run_workflow(db: Session, meeting_id: str, regenerate: bool) -> None:
    meeting = db.get(models.Meeting, meeting_id)
    if not meeting:
        return
    try:
        meeting.status = "processing"
        meeting.error_message = None
        db.commit()
        add_event(db, meeting_id, "load_meeting", "started", "会议处理已启动", 10)

        if not regenerate:
            add_event(db, meeting_id, "load_participants", "running", "读取参会人信息", 20)
            if meeting.source_type == "audio":
                add_event(db, meeting_id, "transcribe_audio", "running", "调用 ASR API 转写中", 30)
                segments = get_asr_provider().transcribe(
                    meeting.file_path,
                    enable_speaker_diarization=meeting.enable_speaker_diarization,
                )
            else:
                add_event(db, meeting_id, "split_transcript", "running", "解析文本会议内容", 35)
                segments = split_text_file(meeting.file_path)
            save_segments(db, meeting_id, segments)
            ensure_speaker_mappings(db, meeting_id, {segment.speaker or "Speaker 1" for segment in segments})
            add_event(db, meeting_id, "detect_speakers", "completed", "说话人标签整理完成", 50)

        add_event(db, meeting_id, "generate_summary", "running", "调用 LLM API 生成摘要", 60)
        generate_summary(db, meeting_id)
        add_event(db, meeting_id, "extract_decisions", "running", "提取关键决策", 66)
        extract_decisions(db, meeting_id)
        add_event(db, meeting_id, "extract_risks", "running", "识别风险点", 72)
        extract_risks(db, meeting_id)
        add_event(db, meeting_id, "extract_action_items", "running", "提取行动项", 78)
        extract_action_items(db, meeting_id)
        add_event(db, meeting_id, "build_vector_index", "running", "构建语义检索索引", 88)
        VectorService().build_meeting_index(db, meeting_id)

        meeting = db.get(models.Meeting, meeting_id)
        if meeting:
            meeting.status = "completed"
            db.commit()
        add_event(db, meeting_id, "mark_completed", "completed", "处理完成", 100)
    except Exception as exc:
        meeting = db.get(models.Meeting, meeting_id)
        if meeting:
            meeting.status = "failed"
            meeting.error_message = str(exc)
            db.commit()
        add_event(db, meeting_id, "failed", "failed", str(exc), 100)


def save_segments(db: Session, meeting_id: str, segments: list[TranscriptionSegment]) -> None:
    db.query(models.TranscriptSegment).filter(models.TranscriptSegment.meeting_id == meeting_id).delete()
    for index, segment in enumerate(segments, start=1):
        db.add(
            models.TranscriptSegment(
                meeting_id=meeting_id,
                sequence=index,
                start_time=segment.start_time,
                end_time=segment.end_time,
                speaker=segment.speaker or "Speaker 1",
                content=segment.content,
            )
        )
    db.commit()


def split_text_file(file_path: str) -> list[TranscriptionSegment]:
    text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        lines = [text.strip()] if text.strip() else ["空文本会议"]
    segments: list[TranscriptionSegment] = []
    speaker_map: dict[str, str] = {}
    sequence = 0
    for line in lines:
        match = re.match(r"^([^:：]{1,30})[:：]\s*(.+)$", line)
        if match:
            speaker = normalize_speaker(match.group(1), speaker_map)
            content = match.group(2)
        else:
            speaker = "Speaker 1"
            content = line
        segments.append(
            TranscriptionSegment(
                start_time=float(sequence * 10),
                end_time=float(sequence * 10 + 8),
                speaker=speaker,
                content=content,
            )
        )
        sequence += 1
    return segments
