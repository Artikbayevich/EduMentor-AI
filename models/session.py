import enum
from sqlalchemy import String, Text, Enum, ForeignKey, Integer, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.base import UUIDMixin, TimestampMixin


class SessionStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class Session(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "sessions"

    student_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    mentor_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus), default=SessionStatus.pending, nullable=False
    )
    scheduled_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    student = relationship("User", back_populates="sessions", foreign_keys=[student_id])
    mentor = relationship("User", back_populates="mentor_sessions", foreign_keys=[mentor_id])

    def __repr__(self) -> str:
        return f"<Session {self.title} [{self.status}]>"
