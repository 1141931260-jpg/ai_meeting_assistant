from sqlalchemy.orm import Session

from app import models


def add_event(db: Session, meeting_id: str, step: str, status: str, message: str, progress: int) -> models.ProcessingEvent:
    event = models.ProcessingEvent(
        meeting_id=meeting_id,
        step=step,
        status=status,
        message=message,
        progress=progress,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
