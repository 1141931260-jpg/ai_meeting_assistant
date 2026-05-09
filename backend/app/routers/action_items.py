from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.schemas import ActionItemRead, ActionItemUpdate

router = APIRouter(prefix="/api", tags=["action items"])


@router.get("/meetings/{meeting_id}/action-items", response_model=list[ActionItemRead])
def list_action_items(meeting_id: str, db: Session = Depends(get_db)):
    return db.query(models.ActionItem).filter(models.ActionItem.meeting_id == meeting_id).all()


@router.patch("/action-items/{action_item_id}", response_model=ActionItemRead)
def patch_action_item(action_item_id: str, payload: ActionItemUpdate, db: Session = Depends(get_db)):
    item = db.get(models.ActionItem, action_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="行动项不存在")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item
