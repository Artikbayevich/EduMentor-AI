"""
api/v1/endpoints/dashboard.py — Student dashboard endpoints.

GET /dashboard/overview               → nb_summary, deadlines, coin_balance, rank
GET /dashboard/subjects               → subjects with grades and NB counts
GET /dashboard/attendance/{subject}   → attendance history + chart data points
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_active_user
from core.config import settings
from core.database import get_db
from models.user import User, LeaderboardEntry
from services.nb_service import (
    check_nb_status,
    get_upcoming_deadlines,
    nb_status_to_dict,
    deadline_to_dict,
    RiskLevel,
)
from services.hemis import make_hemis_client

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ── Response schemas ──────────────────────────────────────────────────────────

class NBSummaryItem(BaseModel):
    subject:    str
    current_nb: int
    max_nb:     int
    remaining:  int
    risk_level: str
    percentage: float


class DeadlineItem(BaseModel):
    subject:   str
    type:      str
    date:      str
    time:      str
    room:      str
    teacher:   str
    days_away: int
    is_exam:   bool
    note:      str | None = None


class LeaderboardInfo(BaseModel):
    rank_university: int | None
    rank_national:   int | None
    total_coins:     float


class DashboardOverview(BaseModel):
    full_name:          str
    university:         str
    faculty:            str
    course:             int
    coin_balance:       float
    nb_summary:         list[NBSummaryItem]
    danger_count:       int         # subjects with HIGH or CRITICAL risk
    upcoming_deadlines: list[DeadlineItem]
    leaderboard:        LeaderboardInfo
    attendance_pct:     float


class SubjectItem(BaseModel):
    subject:     str
    grade:       float | None
    max_grade:   float
    nb_count:    int
    nb_limit:    int
    risk_level:  str
    semester:    int
    teacher:     str
    graded:      bool


class AttendancePoint(BaseModel):
    date:    str
    status:  str          # present | absent | excused
    nb_count: int


class AttendanceHistory(BaseModel):
    subject:        str
    total_classes:  int
    present_count:  int
    absent_count:   int
    attendance_pct: float
    nb_count:       int
    nb_limit:       int
    risk_level:     str
    records:        list[AttendancePoint]
    chart_data:     list[dict]    # [{label: date, present: bool}]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/overview",
    response_model=DashboardOverview,
    summary="Full dashboard overview for the authenticated student",
)
async def get_overview(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardOverview:
    access_token = ""   # TODO: retrieve from Redis once HEMIS token storage is wired

    # Parallel data fetch (sequential here for clarity; use asyncio.gather in prod)
    nb_statuses  = await check_nb_status(current_user.id, access_token)
    deadlines    = await get_upcoming_deadlines(current_user.id, access_token, days=7)

    # Leaderboard entry
    lb_result = await db.execute(
        select(LeaderboardEntry).where(LeaderboardEntry.user_id == current_user.id)
    )
    lb: LeaderboardEntry | None = lb_result.scalar_one_or_none()

    # Attendance % — inverse of absence ratio
    total_nb  = sum(s.current_nb for s in nb_statuses)
    total_max = sum(s.max_nb     for s in nb_statuses) or 1
    attend_pct = round(max(0.0, (1 - total_nb / (total_max * 4)) * 100), 1)

    danger_count = sum(
        1 for s in nb_statuses
        if s.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
    )

    # Pull profile extras from HEMIS mock if not stored in DB
    async with make_hemis_client(access_token) as client:
        info = await client.get_student_info()

    return DashboardOverview(
        full_name=current_user.full_name,
        university=info.get("university", current_user.university if hasattr(current_user, "university") else ""),
        faculty=info.get("faculty", ""),
        course=info.get("course", 1),
        coin_balance=float(current_user.coin_balance or 0),
        nb_summary=[NBSummaryItem(**nb_status_to_dict(s)) for s in nb_statuses],
        danger_count=danger_count,
        upcoming_deadlines=[DeadlineItem(**deadline_to_dict(d)) for d in deadlines],
        leaderboard=LeaderboardInfo(
            rank_university=lb.rank_university if lb else None,
            rank_national=lb.rank_national     if lb else None,
            total_coins=float(lb.total_coins)  if lb else float(current_user.coin_balance or 0),
        ),
        attendance_pct=attend_pct,
    )


@router.get(
    "/subjects",
    response_model=list[SubjectItem],
    summary="All subjects with grades, NB count, and risk level",
)
async def get_subjects(
    current_user: User = Depends(get_current_active_user),
) -> list[SubjectItem]:
    access_token = ""
    async with make_hemis_client(access_token) as client:
        grades = await client.get_grades()

    nb_statuses = await check_nb_status(current_user.id, access_token)
    nb_map = {s.subject: s for s in nb_statuses}

    items: list[SubjectItem] = []
    for g in grades:
        nb = nb_map.get(g["subject"])
        items.append(
            SubjectItem(
                subject=g["subject"],
                grade=g.get("grade"),
                max_grade=g.get("max_grade", 100.0),
                nb_count=g.get("nb_count", nb.current_nb if nb else 0),
                nb_limit=g.get("nb_limit", nb.max_nb if nb else 4),
                risk_level=(nb.risk_level.value if nb else RiskLevel.LOW.value),
                semester=g.get("semester", 1),
                teacher=g.get("teacher", "—"),
                graded=g.get("graded", g.get("grade") is not None),
            )
        )
    return items


@router.get(
    "/attendance/{subject}",
    response_model=AttendanceHistory,
    summary="Attendance history and chart data for a specific subject",
)
async def get_attendance_history(
    subject: str = Path(..., description="Subject name (URL-encoded)", example="Fizika"),
    current_user: User = Depends(get_current_active_user),
) -> AttendanceHistory:
    access_token = ""
    async with make_hemis_client(access_token) as client:
        all_records = await client.get_attendance()

    # Filter to this subject
    subject_records = [r for r in all_records if r["subject"].lower() == subject.lower()]
    if not subject_records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No attendance data found for subject: {subject!r}",
        )

    # Compute stats
    total   = len(subject_records)
    absent  = sum(1 for r in subject_records if r["status"] == "absent")
    present = total - absent

    nb_count = subject_records[0].get("nb_count", absent)
    nb_limit = subject_records[0].get("nb_limit", 4)

    from services.nb_service import _classify_risk
    risk = _classify_risk(nb_count, nb_limit)

    attend_pct = round((present / total) * 100, 1) if total else 0.0

    # Sort chronologically
    subject_records.sort(key=lambda r: r["date"])

    records = [
        AttendancePoint(
            date=r["date"],
            status=r["status"],
            nb_count=r.get("nb_count", nb_count),
        )
        for r in subject_records
    ]

    # Chart data — consecutive attendance run with cumulative NB
    running_nb = 0
    chart_data: list[dict] = []
    for r in subject_records:
        if r["status"] == "absent":
            running_nb += 1
        chart_data.append({
            "date":       r["date"],
            "present":    r["status"] != "absent",
            "status":     r["status"],
            "cumulative_nb": running_nb,
            "nb_limit":   nb_limit,
        })

    return AttendanceHistory(
        subject=subject,
        total_classes=total,
        present_count=present,
        absent_count=absent,
        attendance_pct=attend_pct,
        nb_count=nb_count,
        nb_limit=nb_limit,
        risk_level=risk.value,
        records=records,
        chart_data=chart_data,
    )
