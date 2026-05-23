import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from models.user import UserRole


# ── Shared ──────────────────────────────────────────────────────────────────
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    role: UserRole = UserRole.student


# ── Create ───────────────────────────────────────────────────────────────────
class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


# ── Update ───────────────────────────────────────────────────────────────────
class UserUpdate(BaseModel):
    full_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    password: str | None = Field(None, min_length=8, max_length=128)


# ── Response ─────────────────────────────────────────────────────────────────
class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime


# ── Auth ─────────────────────────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: datetime
    type: str
