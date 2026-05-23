"""
api/v1/endpoints/leaderboard.py — Leaderboard and gamification rankings.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.deps import get_current_active_user
from core.database import get_db
from models.user import User, LeaderboardEntry

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class LeaderboardItem(BaseModel):
    user_id:         uuid.UUID
    full_name:       str
    university:      str
    total_coins:     float
    rank_national:   int | None
    rank_university: int | None


class LeaderboardResponse(BaseModel):
    total: int
    items: list[LeaderboardItem]


class MyRankResponse(BaseModel):
    user_id:         uuid.UUID
    total_coins:     float
    rank_national:   int | None
    rank_university: int | None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/university",
    response_model=LeaderboardResponse,
    summary="Top 50 students in current user's university",
)
async def get_university_leaderboard(
    skip:  int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> LeaderboardResponse:
    query = select(LeaderboardEntry).join(LeaderboardEntry.user).where(
        User.university == current_user.university
    )

    total_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(total_query)

    query = query.order_by(LeaderboardEntry.rank_university.asc()).offset(skip).limit(limit)
    query = query.options(selectinload(LeaderboardEntry.user))
    
    result = await db.execute(query)
    items = result.scalars().all()

    return LeaderboardResponse(
        total=total or 0,
        items=[
            LeaderboardItem(
                user_id=item.user_id,
                full_name=item.user.full_name,
                university=item.university,
                total_coins=float(item.total_coins),
                rank_national=item.rank_national,
                rank_university=item.rank_university,
            ) for item in items
        ]
    )


@router.get(
    "/national",
    response_model=LeaderboardResponse,
    summary="Top 100 students across all universities",
)
async def get_national_leaderboard(
    skip:  int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> LeaderboardResponse:
    query = select(LeaderboardEntry).order_by(LeaderboardEntry.rank_national.asc())

    total_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(total_query)

    query = query.offset(skip).limit(limit).options(selectinload(LeaderboardEntry.user))
    
    result = await db.execute(query)
    items = result.scalars().all()

    return LeaderboardResponse(
        total=total or 0,
        items=[
            LeaderboardItem(
                user_id=item.user_id,
                full_name=item.user.full_name,
                university=item.university,
                total_coins=float(item.total_coins),
                rank_national=item.rank_national,
                rank_university=item.rank_university,
            ) for item in items
        ]
    )


@router.get(
    "/my-rank",
    response_model=MyRankResponse,
    summary="Get current user's leaderboard rank",
)
async def get_my_rank(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MyRankResponse:
    lb_result = await db.execute(
        select(LeaderboardEntry).where(LeaderboardEntry.user_id == current_user.id)
    )
    lb: LeaderboardEntry | None = lb_result.scalar_one_or_none()

    if not lb:
        return MyRankResponse(
            user_id=current_user.id,
            total_coins=float(current_user.coin_balance or 0),
            rank_national=None,
            rank_university=None,
        )

    return MyRankResponse(
        user_id=current_user.id,
        total_coins=float(lb.total_coins),
        rank_national=lb.rank_national,
        rank_university=lb.rank_university,
    )
