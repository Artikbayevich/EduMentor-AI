"""
api/v1/endpoints/p2p.py — Peer-to-peer tutoring request and match management.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, or_, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.deps import get_current_active_user
from core.database import get_db
from models.user import User, P2PRequest, P2PMatch, Notification, NotificationType

router = APIRouter(prefix="/p2p", tags=["P2P Tutoring"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class P2PRequestCreate(BaseModel):
    subject:     str
    description: str
    coin_offer:  int


class P2PRequestResponse(BaseModel):
    id:            uuid.UUID
    requester_id:  uuid.UUID
    requester_name: str
    subject:       str
    description:   str
    coin_offer:    int
    status:        str
    created_at:    str


class P2PMatchResponse(BaseModel):
    id:                 uuid.UUID
    request_id:         uuid.UUID
    subject:            str
    requester_id:       uuid.UUID
    requester_name:     str
    helper_id:          uuid.UUID
    helper_name:        str
    status:             str
    coins_transferred:  int | None
    created_at:         str


class PaginatedP2PRequests(BaseModel):
    total: int
    items: list[P2PRequestResponse]


class PaginatedP2PMatches(BaseModel):
    total: int
    items: list[P2PMatchResponse]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/requests",
    response_model=PaginatedP2PRequests,
    summary="List active P2P help requests",
)
async def list_p2p_requests(
    subject:    str | None = Query(None, description="Filter by exact subject name"),
    university: str | None = Query(None, description="Filter by university name"),
    skip:       int = Query(0, ge=0),
    limit:      int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedP2PRequests:
    query = select(P2PRequest).join(P2PRequest.requester).where(P2PRequest.status == "open")

    if subject:
        query = query.where(P2PRequest.subject.ilike(f"%{subject}%"))
    if university:
        query = query.where(User.university.ilike(f"%{university}%"))

    # Exclude user's own requests from the feed
    query = query.where(P2PRequest.requester_id != current_user.id)

    total_query = select(db.func.count()).select_from(query.subquery())
    total = await db.scalar(total_query)

    query = query.order_by(P2PRequest.created_at.desc()).offset(skip).limit(limit)
    query = query.options(selectinload(P2PRequest.requester))
    
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedP2PRequests(
        total=total or 0,
        items=[
            P2PRequestResponse(
                id=item.id,
                requester_id=item.requester_id,
                requester_name=item.requester.full_name,
                subject=item.subject,
                description=item.description,
                coin_offer=item.coin_offer,
                status=item.status,
                created_at=item.created_at.isoformat(),
            ) for item in items
        ]
    )


@router.post(
    "/requests",
    response_model=P2PRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new help request",
)
async def create_p2p_request(
    data: P2PRequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> P2PRequestResponse:
    if current_user.coin_balance is None or current_user.coin_balance < data.coin_offer:
        raise HTTPException(status_code=400, detail="Insufficient coin balance.")

    req = P2PRequest(
        requester_id=current_user.id,
        subject=data.subject,
        description=data.description,
        coin_offer=data.coin_offer,
        status="open",
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    return P2PRequestResponse(
        id=req.id,
        requester_id=req.requester_id,
        requester_name=current_user.full_name,
        subject=req.subject,
        description=req.description,
        coin_offer=req.coin_offer,
        status=req.status,
        created_at=req.created_at.isoformat(),
    )


@router.post(
    "/requests/{request_id}/respond",
    response_model=P2PMatchResponse,
    summary="Offer to help with a specific request",
)
async def respond_to_request(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> P2PMatchResponse:
    req_query = select(P2PRequest).options(selectinload(P2PRequest.requester)).where(P2PRequest.id == request_id)
    result = await db.execute(req_query)
    req: P2PRequest | None = result.scalar_one_or_none()

    if not req or req.status != "open":
        raise HTTPException(status_code=404, detail="Request not found or already closed.")
    if req.requester_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot respond to your own request.")

    # Create match
    match = P2PMatch(
        request_id=req.id,
        helper_id=current_user.id,
        status="active",
    )
    req.status = "assigned"
    db.add(match)
    
    # Notify requester
    db.add(Notification(
        user_id=req.requester_id,
        type=NotificationType.p2p_match,
        message=f"{current_user.full_name} sizning '{req.subject}' so'rovingiz bo'yicha yordam berishga tayyor!",
        is_read=False,
    ))
    
    await db.commit()
    await db.refresh(match)

    return P2PMatchResponse(
        id=match.id,
        request_id=req.id,
        subject=req.subject,
        requester_id=req.requester_id,
        requester_name=req.requester.full_name,
        helper_id=current_user.id,
        helper_name=current_user.full_name,
        status=match.status,
        coins_transferred=None,
        created_at=match.created_at.isoformat(),
    )


@router.post(
    "/matches/{match_id}/complete",
    summary="Mark a P2P session as complete and transfer coins",
)
async def complete_match(
    match_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(P2PMatch).options(
        selectinload(P2PMatch.request).selectinload(P2PRequest.requester),
        selectinload(P2PMatch.helper)
    ).where(P2PMatch.id == match_id)
    
    result = await db.execute(query)
    match: P2PMatch | None = result.scalar_one_or_none()

    if not match or match.status != "active":
        raise HTTPException(status_code=404, detail="Active match not found.")

    req = match.request
    # Only requester or helper can complete
    if current_user.id not in (req.requester_id, match.helper_id):
        raise HTTPException(status_code=403, detail="Not authorized to complete this match.")

    if req.requester.coin_balance < req.coin_offer:
        raise HTTPException(status_code=400, detail="Requester does not have enough coins to complete transaction.")

    # Transfer coins
    req.requester.coin_balance -= req.coin_offer
    match.helper.coin_balance = (match.helper.coin_balance or 0) + req.coin_offer

    match.status = "completed"
    match.coins_transferred = req.coin_offer
    req.status = "completed"

    await db.commit()
    return {"message": "Match completed successfully", "coins_transferred": req.coin_offer}


@router.get(
    "/my-matches",
    response_model=PaginatedP2PMatches,
    summary="Get user's active and past matches (both as requester and helper)",
)
async def get_my_matches(
    skip:  int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedP2PMatches:
    query = select(P2PMatch).join(P2PMatch.request).where(
        or_(
            P2PMatch.helper_id == current_user.id,
            P2PRequest.requester_id == current_user.id
        )
    )

    total_query = select(db.func.count()).select_from(query.subquery())
    total = await db.scalar(total_query)

    query = query.order_by(P2PMatch.created_at.desc()).offset(skip).limit(limit)
    query = query.options(
        selectinload(P2PMatch.request).selectinload(P2PRequest.requester),
        selectinload(P2PMatch.helper)
    )
    
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedP2PMatches(
        total=total or 0,
        items=[
            P2PMatchResponse(
                id=item.id,
                request_id=item.request_id,
                subject=item.request.subject,
                requester_id=item.request.requester_id,
                requester_name=item.request.requester.full_name,
                helper_id=item.helper_id,
                helper_name=item.helper.full_name,
                status=item.status,
                coins_transferred=item.coins_transferred,
                created_at=item.created_at.isoformat(),
            ) for item in items
        ]
    )
