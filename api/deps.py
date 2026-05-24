import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import decode_token
from core.redis import get_redis
from models.user import User, UserRole
from services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    svc = UserService(db)
    user = await svc.get_by_id(uuid.UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


async def get_current_active_user(db: AsyncSession = Depends(get_db)):
    # Hackathon Demo Mode: Always return the main seeded user
    from sqlalchemy import select
    from models.user import User
    
    result = await db.execute(select(User).where(User.hemis_id == "admin_hemis"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Main demo user not found (did you run seed.py?)")
    return user


def require_role(*roles: UserRole):
    async def checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return checker
