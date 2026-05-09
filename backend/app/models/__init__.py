import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def uuid_str() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.utcnow()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class UpdatedAtMixin(TimestampMixin):
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc, nullable=False)


class Meeting(UpdatedAtMixin, Base):
    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    enable_speaker_diarization: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)

    participants: Mapped[list["Participant"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    speaker_mappings: Mapped[list["SpeakerMapping"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    transcript_segments: Mapped[list["TranscriptSegment"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan", order_by="TranscriptSegment.sequence"
    )
    summary: Mapped["MeetingSummary | None"] = relationship(
        back_populates="meeting", cascade="all, delete-orphan", uselist=False
    )
    decisions: Mapped[list["Decision"]] = relationship(back_populates="meeting", cascade="all, delete-orphan")
    risks: Mapped[list["Risk"]] = relationship(back_populates="meeting", cascade="all, delete-orphan")
    action_items: Mapped[list["ActionItem"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    events: Mapped[list["ProcessingEvent"]] = relationship(back_populates="meeting", cascade="all, delete-orphan")


class Participant(UpdatedAtMixin, Base):
    __tablename__ = "participants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(255))

    meeting: Mapped[Meeting] = relationship(back_populates="participants")


class SpeakerMapping(UpdatedAtMixin, Base):
    __tablename__ = "speaker_mappings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    speaker_label: Mapped[str] = mapped_column(String(80), nullable=False)
    participant_id: Mapped[str | None] = mapped_column(ForeignKey("participants.id", ondelete="SET NULL"))
    display_name: Mapped[str | None] = mapped_column(String(120))

    meeting: Mapped[Meeting] = relationship(back_populates="speaker_mappings")
    participant: Mapped[Participant | None] = relationship()


class TranscriptSegment(TimestampMixin, Base):
    __tablename__ = "transcript_segments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    speaker: Mapped[str] = mapped_column(String(80), default="Speaker 1", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    meeting: Mapped[Meeting] = relationship(back_populates="transcript_segments")


class MeetingSummary(TimestampMixin, Base):
    __tablename__ = "meeting_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), unique=True)
    overview: Mapped[str] = mapped_column(Text, nullable=False)
    key_points: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    conclusion: Mapped[str] = mapped_column(Text, nullable=False)
    speaker_summary: Mapped[dict | None] = mapped_column(JSON)

    meeting: Mapped[Meeting] = relationship(back_populates="summary")


class Decision(TimestampMixin, Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str | None] = mapped_column(String(120))
    reason: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[str | None] = mapped_column(Text)
    speaker: Mapped[str | None] = mapped_column(String(120))

    meeting: Mapped[Meeting] = relationship(back_populates="decisions")


class Risk(TimestampMixin, Base):
    __tablename__ = "risks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    risk_type: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    owner: Mapped[str | None] = mapped_column(String(120))
    speaker: Mapped[str | None] = mapped_column(String(120))
    evidence: Mapped[str | None] = mapped_column(Text)
    suggestion: Mapped[str | None] = mapped_column(Text)

    meeting: Mapped[Meeting] = relationship(back_populates="risks")


class ActionItem(UpdatedAtMixin, Base):
    __tablename__ = "action_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    owner: Mapped[str | None] = mapped_column(String(120))
    owner_participant_id: Mapped[str | None] = mapped_column(ForeignKey("participants.id", ondelete="SET NULL"))
    due_date: Mapped[str | None] = mapped_column(String(40))
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="todo", nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text)
    source_speaker: Mapped[str | None] = mapped_column(String(120))

    meeting: Mapped[Meeting] = relationship(back_populates="action_items")
    owner_participant: Mapped[Participant | None] = relationship()


class ProcessingEvent(TimestampMixin, Base):
    __tablename__ = "processing_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    step: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    meeting: Mapped[Meeting] = relationship(back_populates="events")
