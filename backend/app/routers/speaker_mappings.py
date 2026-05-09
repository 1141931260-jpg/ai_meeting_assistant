from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.schemas import SpeakerMappingBatchUpdate, SpeakerMappingRead
from app.services.speaker_mapping_service import update_mappings

router = APIRouter(prefix="/api/meetings/{meeting_id}/speaker-mappings", tags=["speaker mappings"])


@router.get("", response_model=list[SpeakerMappingRead])
def list_mappings(meeting_id: str, db: Session = Depends(get_db)):
    return db.query(models.SpeakerMapping).filter(models.SpeakerMapping.meeting_id == meeting_id).all()


@router.patch("", response_model=list[SpeakerMappingRead])
def patch_mappings(meeting_id: str, payload: SpeakerMappingBatchUpdate, db: Session = Depends(get_db)):
    if not db.get(models.Meeting, meeting_id):
        raise HTTPException(status_code=404, detail="会议不存在")
    return update_mappings(db, meeting_id, payload.mappings)
