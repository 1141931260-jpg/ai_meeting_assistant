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
        {"overview": "摘要生成失败", "key_points": [], "conclusion": "", "speaker_summary": {}},
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
    db.commit()
    db.refresh(summary)
    return summary
