from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routers import action_items, meetings, participants, search, speaker_mappings


settings = get_settings()
app = FastAPI(title="AI Meeting Assistant", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def health():
    return {"ok": True}


app.include_router(meetings.router)
app.include_router(participants.router)
app.include_router(speaker_mappings.router)
app.include_router(action_items.router)
app.include_router(search.router)
