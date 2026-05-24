import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


# ─── Enums ────────────────────────────────────────────────────────────────────

class P2PStatus(str, enum.Enum):
    open = "open"
    matched = "matched"
    completed = "completed"
    cancelled = "cancelled"


class MatchStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    completed = "completed"


class SkillType(str, enum.Enum):
    can_teach = "can_teach"
    want_learn = "want_learn"

class UserRole(str, enum.Enum):
    student = "student"
    admin = "admin"


class NotificationType(str, enum.Enum):
    system = "system"
    p2p_request = "p2p_request"
    p2p_match = "p2p_match"
    coin_transfer = "coin_transfer"
    subject_alert = "subject_alert"
    leaderboard = "leaderboard"


# ─── Models ───────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    hemis_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    university: Mapped[str] = mapped_column(String(255), nullable=False)
    faculty: Mapped[str] = mapped_column(String(255), nullable=False)
    course: Mapped[int] = mapped_column(Integer, nullable=False)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True, nullable=True)
    coin_balance: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.student, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    subjects: Mapped[list["Subject"]] = relationship(
        "Subject", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )
    p2p_requests: Mapped[list["P2PRequest"]] = relationship(
        "P2PRequest", back_populates="requester", cascade="all, delete-orphan"
    )
    p2p_matches_as_helper: Mapped[list["P2PMatch"]] = relationship(
        "P2PMatch", back_populates="helper"
    )
    skills: Mapped[list["Skill"]] = relationship(
        "Skill", back_populates="user", cascade="all, delete-orphan"
    )
    leaderboard_entry: Mapped["LeaderboardEntry | None"] = relationship(
        "LeaderboardEntry", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    sessions: Mapped[list["Session"]] = relationship(
        "Session", foreign_keys="[Session.student_id]", back_populates="student"
    )
    mentor_sessions: Mapped[list["Session"]] = relationship(
        "Session", foreign_keys="[Session.mentor_id]", back_populates="mentor"
    )

    def __repr__(self) -> str:
        return f"<User {self.full_name!r} hemis={self.hemis_id}>"


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nb_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    nb_limit: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    last_checked: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="subjects")

    def __repr__(self) -> str:
        return f"<Subject {self.name!r} user={self.user_id}>"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")

    def __repr__(self) -> str:
        return f"<Notification type={self.type} user={self.user_id} read={self.is_read}>"


class P2PRequest(Base):
    __tablename__ = "p2p_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    coin_offer: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[P2PStatus] = mapped_column(
        Enum(P2PStatus), default=P2PStatus.open, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    requester: Mapped["User"] = relationship("User", back_populates="p2p_requests")
    matches: Mapped[list["P2PMatch"]] = relationship(
        "P2PMatch", back_populates="request", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<P2PRequest subject={self.subject!r} status={self.status}>"


class P2PMatch(Base):
    __tablename__ = "p2p_matches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("p2p_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    helper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus), default=MatchStatus.pending, nullable=False
    )
    coins_transferred: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    request: Mapped["P2PRequest"] = relationship("P2PRequest", back_populates="matches")
    helper: Mapped["User | None"] = relationship("User", back_populates="p2p_matches_as_helper")

    def __repr__(self) -> str:
        return f"<P2PMatch request={self.request_id} helper={self.helper_id} status={self.status}>"


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[SkillType] = mapped_column(Enum(SkillType), nullable=False)
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)  # e.g. 1–5

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="skills")

    def __repr__(self) -> str:
        return f"<Skill {self.skill_name!r} type={self.type} user={self.user_id}>"


class LeaderboardEntry(Base):
    __tablename__ = "leaderboard_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    university: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    total_coins: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    rank_university: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rank_national: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="leaderboard_entry")

    def __repr__(self) -> str:
        return (
            f"<LeaderboardEntry user={self.user_id} "
            f"coins={self.total_coins} rank_nat={self.rank_national}>"
        )
