import uuid
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from models.session import SessionStatus


class SessionBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str | None = None
    subject: str = Field(..., max_length=100)
    scheduled_at: datetime | None = None
    duration_minutes: int = Field(default=60, ge=15, le=480)


class SessionCreate(SessionBase):
    mentor_id: uuid.UUID | None = None


class SessionUpdate(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=255)
    description: str | None = None
    subject: str | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = Field(None, ge=15, le=480)
    status: SessionStatus | None = None
    rating: float | None = Field(None, ge=1.0, le=5.0)
    feedback: str | None = None


class SessionResponse(SessionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    mentor_id: uuid.UUID | None
    status: SessionStatus
    rating: float | None
    feedback: str | None
    created_at: datetime
    updated_at: datetime
