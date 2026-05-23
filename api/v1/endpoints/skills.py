"""
api/v1/endpoints/skills.py — User skill management and AI matching.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_active_user
from core.database import get_db
from models.user import User, Skill, Notification, NotificationType
from services.skill_matching_service import find_matches_for_user

router = APIRouter(prefix="/skills", tags=["Skills & Matching"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class SkillBase(BaseModel):
    skill_name: str
    type:       str  # "can_teach" or "want_learn"
    level:      int | None = None


class SkillProfileResponse(BaseModel):
    user_id:    uuid.UUID
    full_name:  str
    university: str
    can_teach:  list[SkillBase]
    want_learn: list[SkillBase]


class SkillProfileUpdate(BaseModel):
    can_teach:  list[SkillBase]
    want_learn: list[SkillBase]


class MatchItem(BaseModel):
    user_id:         uuid.UUID
    full_name:       str
    university:      str
    match_score:     float
    match_type:      str
    can_help_with:   list[str]
    needs_help_with: list[str]
    common_learning: list[str]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/profile/{user_id}",
    response_model=SkillProfileResponse,
    summary="Get user's skill profile",
)
async def get_skill_profile(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SkillProfileResponse:
    user_result = await db.execute(select(User).where(User.id == user_id))
    user: User | None = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    skills_result = await db.execute(select(Skill).where(Skill.user_id == user_id))
    skills = list(skills_result.scalars().all())

    return SkillProfileResponse(
        user_id=user.id,
        full_name=user.full_name,
        university=user.university,
        can_teach=[SkillBase(skill_name=s.skill_name, type=s.type, level=s.level) for s in skills if s.type == "can_teach"],
        want_learn=[SkillBase(skill_name=s.skill_name, type=s.type, level=s.level) for s in skills if s.type == "want_learn"],
    )


@router.put(
    "/profile",
    response_model=SkillProfileResponse,
    summary="Update current user's skill profile",
)
async def update_skill_profile(
    data: SkillProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SkillProfileResponse:
    # Delete existing skills
    await db.execute(Skill.__table__.delete().where(Skill.user_id == current_user.id))

    new_skills = []
    for skill_list in (data.can_teach, data.want_learn):
        for s in skill_list:
            new_skills.append(
                Skill(
                    user_id=current_user.id,
                    skill_name=s.skill_name,
                    type=s.type,
                    level=s.level,
                )
            )

    if new_skills:
        db.add_all(new_skills)
        
    await db.commit()

    return SkillProfileResponse(
        user_id=current_user.id,
        full_name=current_user.full_name,
        university=current_user.university,
        can_teach=data.can_teach,
        want_learn=data.want_learn,
    )


@router.get(
    "/matches",
    response_model=list[MatchItem],
    summary="Get AI-matched users for the current user",
)
async def get_matches(
    top_k: int = 10,
    min_score: float = 5.0,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[MatchItem]:
    matches = await find_matches_for_user(
        user_id=current_user.id,
        db=db,
        top_k=top_k,
        min_score=min_score,
    )

    return [
        MatchItem(
            user_id=m.user_id,
            full_name=m.full_name,
            university=m.university,
            match_score=m.match_score,
            match_type=m.match_type.value,
            can_help_with=m.can_help_with,
            needs_help_with=m.needs_help_with,
            common_learning=m.common_learning,
        ) for m in matches
    ]


@router.post(
    "/matches/{target_id}/connect",
    summary="Send a connection request to a matched user",
)
async def connect_with_match(
    target_id: uuid.UUID,
    message: str | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if target_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot connect with yourself")

    target_result = await db.execute(select(User).where(User.id == target_id))
    target: User | None = target_result.scalar_one_or_none()
    
    if not target:
        raise HTTPException(status_code=404, detail="Target user not found")

    msg = f"{current_user.full_name} siz bilan birga o'qish/yordam berish maqsadida bog'lanmoqchi."
    if message:
        msg += f"\n\nXabar: {message}"

    db.add(Notification(
        user_id=target.id,
        type=NotificationType.p2p_match,
        message=msg,
        is_read=False,
    ))
    
    await db.commit()
    return {"message": "Connection request sent"}
