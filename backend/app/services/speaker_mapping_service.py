from sqlalchemy.orm import Session

from app import models
from app.schemas import SpeakerMappingInput


def display_name_for_speaker(db: Session, meeting_id: str, speaker: str) -> tuple[str, str | None]:
    mapping = (
        db.query(models.SpeakerMapping)
        .filter(models.SpeakerMapping.meeting_id == meeting_id, models.SpeakerMapping.speaker_label == speaker)
        .first()
    )
    if not mapping:
        return speaker, None
    if mapping.participant:
        return mapping.participant.name, mapping.participant_id
    return mapping.display_name or speaker, mapping.participant_id


def speaker_display_map(db: Session, meeting_id: str) -> dict[str, str]:
    mappings = db.query(models.SpeakerMapping).filter(models.SpeakerMapping.meeting_id == meeting_id).all()
    result: dict[str, str] = {}
    for mapping in mappings:
        if mapping.participant:
            result[mapping.speaker_label] = mapping.participant.name
        elif mapping.display_name:
            result[mapping.speaker_label] = mapping.display_name
    return result


def ensure_speaker_mappings(db: Session, meeting_id: str, labels: set[str]) -> None:
    existing = {
        item.speaker_label
        for item in db.query(models.SpeakerMapping).filter(models.SpeakerMapping.meeting_id == meeting_id).all()
    }
    for label in sorted(labels):
        if label not in existing:
            db.add(models.SpeakerMapping(meeting_id=meeting_id, speaker_label=label))
    db.commit()


def update_mappings(db: Session, meeting_id: str, inputs: list[SpeakerMappingInput]) -> list[models.SpeakerMapping]:
    updated: list[models.SpeakerMapping] = []
    for item in inputs:
        mapping = (
            db.query(models.SpeakerMapping)
            .filter(models.SpeakerMapping.meeting_id == meeting_id, models.SpeakerMapping.speaker_label == item.speaker_label)
            .first()
        )
        if not mapping:
            mapping = models.SpeakerMapping(meeting_id=meeting_id, speaker_label=item.speaker_label)
            db.add(mapping)
        mapping.participant_id = item.participant_id
        mapping.display_name = item.display_name
        updated.append(mapping)
    db.commit()
    for mapping in updated:
        db.refresh(mapping)
    return updated
