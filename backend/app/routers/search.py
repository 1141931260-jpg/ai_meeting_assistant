from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import SearchRequest, SearchResult
from app.services.vector_service import VectorService

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=list[SearchResult])
def search(payload: SearchRequest, db: Session = Depends(get_db)):
    return VectorService().search(db, payload.query, payload.top_k)
