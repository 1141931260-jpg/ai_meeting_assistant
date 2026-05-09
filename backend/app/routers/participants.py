from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.schemas import ParticipantCreate, ParticipantRead, ParticipantUpdate
from app.services.participant_service import create_participant, update_participant

router = APIRouter(prefix="/api", tags=["participants"])


@router.get("/meetings/{meeting_id}/participants", response_model=list[ParticipantRead])
def list_participants(meeting_id: str, db: Session = Depends(get_db)):
    return db.query(models.Participant).filter(models.Participant.meeting_id == meeting_id).all()


@router.post("/meetings/{meeting_id}/participants", response_model=ParticipantRead)
def add_participant(meeting_id: str, payload: ParticipantCreate, db: Session = Depends(get_db)):
    if not db.get(models.Meeting, meeting_id):
        raise HTTPException(status_code=404, detail="会议不存在")
    return create_participant(db, meeting_id, payload)


@router.patch("/participants/{participant_id}", response_model=ParticipantRead)
def patch_participant(participant_id: str, payload: ParticipantUpdate, db: Session = Depends(get_db)):
    participant = db.get(models.Participant, participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="参会人不存在")
    return update_participant(db, participant, payload)


@router.delete("/participants/{participant_id}")
def delete_participant(participant_id: str, db: Session = Depends(get_db)):
    participant = db.get(models.Participant, participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="参会人不存在")
    db.delete(participant)
    db.commit()
    return {"ok": True}
