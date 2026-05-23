import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.session import Session, SessionStatus
from schemas.session import SessionCreate, SessionUpdate


class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, session_id: uuid.UUID) -> Session | None:
        result = await self.db.execute(select(Session).where(Session.id == session_id))
        return result.scalar_one_or_none()

    async def get_by_student(self, student_id: uuid.UUID) -> list[Session]:
        result = await self.db.execute(
            select(Session).where(Session.student_id == student_id)
        )
        return list(result.scalars().all())

    async def get_by_mentor(self, mentor_id: uuid.UUID) -> list[Session]:
        result = await self.db.execute(
            select(Session).where(Session.mentor_id == mentor_id)
        )
        return list(result.scalars().all())

    async def create(self, student_id: uuid.UUID, payload: SessionCreate) -> Session:
        session = Session(
            student_id=student_id,
            mentor_id=payload.mentor_id,
            title=payload.title,
            description=payload.description,
            subject=payload.subject,
            scheduled_at=payload.scheduled_at,
            duration_minutes=payload.duration_minutes,
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def update(self, session: Session, payload: SessionUpdate) -> Session:
        data = payload.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(session, field, value)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def cancel(self, session: Session) -> Session:
        session.status = SessionStatus.cancelled
        await self.db.flush()
        return session
