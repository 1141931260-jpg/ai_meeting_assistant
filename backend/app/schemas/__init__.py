from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ParticipantBase(BaseModel):
    name: str
    role: str | None = None
    email: str | None = None


class ParticipantCreate(ParticipantBase):
    pass


class ParticipantUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    email: str | None = None


class ParticipantRead(ParticipantBase, ORMModel):
    id: str
    meeting_id: str
    created_at: datetime
    updated_at: datetime


class MeetingRead(ORMModel):
    id: str
    title: str
    description: str | None
    source_type: Literal["audio", "text"]
    status: str
    enable_speaker_diarization: bool
    original_filename: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class MeetingDetail(MeetingRead):
    participants: list[ParticipantRead] = []


class SpeakerMappingInput(BaseModel):
    speaker_label: str
    participant_id: str | None = None
    display_name: str | None = None


class SpeakerMappingBatchUpdate(BaseModel):
    mappings: list[SpeakerMappingInput]


class SpeakerMappingRead(ORMModel):
    id: str
    meeting_id: str
    speaker_label: str
    participant_id: str | None
    display_name: str | None
    created_at: datetime
    updated_at: datetime


class TranscriptSegmentRead(ORMModel):
    id: str
    meeting_id: str
    sequence: int
    start_time: float
    end_time: float
    speaker: str
    participant_id: str | None = None
    display_speaker: str = ""
    content: str
    created_at: datetime


class MeetingSummaryRead(ORMModel):
    id: str
    meeting_id: str
    overview: str
    key_points: list[str]
    conclusion: str
    speaker_summary: dict[str, str] | None = None
    created_at: datetime


class DecisionRead(ORMModel):
    id: str
    meeting_id: str
    content: str
    owner: str | None = None
    reason: str | None = None
    evidence: str | None = None
    speaker: str | None = None
    created_at: datetime


class RiskRead(ORMModel):
    id: str
    meeting_id: str
    risk_type: str
    description: str
    level: Literal["low", "medium", "high"]
    owner: str | None = None
    speaker: str | None = None
    evidence: str | None = None
    suggestion: str | None = None
    created_at: datetime


class ActionItemRead(ORMModel):
    id: str
    meeting_id: str
    title: str
    description: str | None = None
    owner: str | None = None
    owner_participant_id: str | None = None
    due_date: str | None = None
    priority: Literal["low", "medium", "high"]
    status: Literal["todo", "doing", "done"]
    evidence: str | None = None
    source_speaker: str | None = None
    created_at: datetime
    updated_at: datetime


class ActionItemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    owner: str | None = None
    owner_participant_id: str | None = None
    due_date: str | None = None
    priority: Literal["low", "medium", "high"] | None = None
    status: Literal["todo", "doing", "done"] | None = None


class ProcessingEventRead(ORMModel):
    id: str
    meeting_id: str
    step: str
    status: Literal["started", "running", "completed", "failed"]
    message: str
    progress: int
    created_at: datetime


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    meeting_id: str
    meeting_title: str
    content_type: str
    speaker: str | None = None
    participant_name: str | None = None
    content: str
    score: float
    evidence: str | None = None
    metadata: dict[str, Any] = {}


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class MeetingChatRequest(BaseModel):
    question: str = Field(min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)


class MeetingChatResponse(BaseModel):
    meeting_id: str
    answer: str
