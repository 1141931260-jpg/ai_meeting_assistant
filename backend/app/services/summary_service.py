from sqlalchemy.orm import Session

from app import models
from app.services.llm_provider import get_llm_provider, parse_json_object
from app.services.speaker_mapping_service import speaker_display_map


def transcript_prompt_text(db: Session, meeting_id: str) -> str:
    display_map = speaker_display_map(db, meeting_id)
    segments = (
        db.query(models.TranscriptSegment)
        .filter(models.TranscriptSegment.meeting_id == meeting_id)
        .order_by(models.TranscriptSegment.sequence)
        .all()
    )
    lines = []
    for segment in segments:
        speaker = display_map.get(segment.speaker, segment.speaker)
        lines.append(f"[{segment.start_time:.0f}-{segment.end_time:.0f}] {speaker}: {segment.content}")
    return "\n".join(lines)


def generate_summary(db: Session, meeting_id: str) -> models.MeetingSummary:
    prompt = f"""
请根据以下会议转写生成会议摘要，只输出 JSON：
{{
  "title": "不超过20字的会议标题",
  "description": "一句话会议描述",
  "overview": "会议总览",
  "key_points": ["关键点"],
  "conclusion": "结论",
  "speaker_summary": {{"说话人": "主要观点"}}
}}

会议转写：
{transcript_prompt_text(db, meeting_id)}
"""
    data = parse_json_object(
        get_llm_provider().generate(prompt),
        {"title": "", "description": "", "overview": "摘要生成失败", "key_points": [], "conclusion": "", "speaker_summary": {}},
    )
    db.query(models.MeetingSummary).filter(models.MeetingSummary.meeting_id == meeting_id).delete()
    summary = models.MeetingSummary(
        meeting_id=meeting_id,
        overview=str(data.get("overview") or ""),
        key_points=list(data.get("key_points") or []),
        conclusion=str(data.get("conclusion") or ""),
        speaker_summary=data.get("speaker_summary") or {},
    )
    db.add(summary)
    meeting = db.get(models.Meeting, meeting_id)
    if meeting:
        if not meeting.title.strip():
            meeting.title = _fallback_title(
                str(data.get("title") or ""),
                str(data.get("overview") or ""),
                transcript_prompt_text(db, meeting_id),
                meeting.original_filename,
            )
        if not (meeting.description or "").strip():
            meeting.description = _fallback_description(str(data.get("description") or ""), str(data.get("overview") or ""))
    db.commit()
    db.refresh(summary)
    return summary


def _fallback_title(ai_title: str, overview: str, transcript: str, filename: str) -> str:
    for candidate in [ai_title, overview, transcript, filename]:
        value = _clean_generated_text(candidate)
        if value and not _is_placeholder(value):
            return value[:40]
    return "未命名会议"


def _fallback_description(ai_description: str, overview: str) -> str | None:
    for candidate in [ai_description, overview]:
        value = _clean_generated_text(candidate)
        if value and not _is_placeholder(value):
            return value[:300]
    return None


def _clean_generated_text(value: str) -> str:
    return " ".join(str(value or "").replace("\n", " ").split())


def _is_placeholder(value: str) -> bool:
    markers = ["待定", "无法解析", "内容缺失", "无法生成", "未提供", "无标题"]
    return not value.strip("?？ ") or any(marker in value for marker in markers)
