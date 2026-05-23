import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_password_hash, verify_password
from models.user import User
from schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def create(self, payload: UserCreate) -> User:
        user = User(
            email=payload.email,
            username=payload.username,
            full_name=payload.full_name,
            bio=payload.bio,
            role=payload.role,
            hashed_password=get_password_hash(payload.password),
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update(self, user: User, payload: UserUpdate) -> User:
        data = payload.model_dump(exclude_unset=True)
        if "password" in data:
            data["hashed_password"] = get_password_hash(data.pop("password"))
        for field, value in data.items():
            setattr(user, field, value)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def authenticate(self, email: str, password: str) -> User | None:
        user = await self.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

    async def deactivate(self, user: User) -> User:
        user.is_active = False
        await self.db.flush()
        return user
