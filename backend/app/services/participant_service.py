from sqlalchemy.orm import Session

from app import models
from app.schemas import ParticipantCreate, ParticipantUpdate


def create_participant(db: Session, meeting_id: str, payload: ParticipantCreate) -> models.Participant:
    participant = models.Participant(meeting_id=meeting_id, **payload.model_dump())
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant


def update_participant(db: Session, participant: models.Participant, payload: ParticipantUpdate) -> models.Participant:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(participant, key, value)
    db.commit()
    db.refresh(participant)
    return participant
