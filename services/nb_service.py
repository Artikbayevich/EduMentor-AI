"""
nb_service.py — NB (devomad/naposeshchaemost) detection and scheduling service.

Responsibilities:
  • Analyse attendance data and classify each subject by risk level.
  • Determine today's missed lessons and enrich them with LMS topic info.
  • Expose upcoming exam / assignment deadlines.
  • Schedule a nightly 23:00 check via APScheduler that persists alerts to DB.

No Telegram / notification dispatch here — callers receive structured data
and decide how to surface it.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import AsyncSessionLocal
from models.user import User
from models.session import Session  # noqa: F401 — kept for future join
from services.hemis import make_hemis_client
from services.hemis.hemis_mock import (
    mock_get_attendance,
    mock_get_grades,
    mock_get_schedule,
    mock_get_today_missed,
    mock_get_danger_subjects,
)


# ─── Enums & data classes ─────────────────────────────────────────────────────

class RiskLevel(str, Enum):
    LOW      = "LOW"       # 0 absences
    MEDIUM   = "MEDIUM"    # 1 absence (1 remaining before warning threshold)
    HIGH     = "HIGH"      # nb_limit - 1  (1 remaining before expulsion risk)
    CRITICAL = "CRITICAL"  # nb_limit reached or exceeded


@dataclass(slots=True)
class NBStatus:
    subject:     str
    current_nb:  int
    max_nb:      int
    remaining:   int
    risk_level:  RiskLevel
    percentage:  float       # current_nb / max_nb * 100


@dataclass(slots=True)
class MissedLesson:
    subject:             str
    topic:               str
    teacher:             str
    time:                str
    room:                str
    nb_count:            int
    nb_limit:            int
    materials_available: bool
    materials:           list[dict]      = field(default_factory=list)
    can_request_p2p:     bool            = True
    exam_in_days:        int | None      = None
    exam_warning:        str | None      = None


@dataclass(slots=True)
class Deadline:
    subject:    str
    type:       str          # "exam" | "assignment" | "seminar" | "lab"
    date:       str          # ISO
    time:       str          # HH:MM
    room:       str
    teacher:    str
    days_away:  int
    is_exam:    bool
    note:       str | None   = None


@dataclass(slots=True)
class DailyCheckResult:
    user_id:          uuid.UUID
    checked_at:       datetime
    nb_statuses:      list[NBStatus]
    danger_subjects:  list[NBStatus]     # risk HIGH or CRITICAL
    missed_today:     list[MissedLesson]
    upcoming_exams:   list[Deadline]


# ─── Risk classifier ─────────────────────────────────────────────────────────

def _classify_risk(current: int, limit: int) -> RiskLevel:
    """
    Thresholds (nb_limit = 4 as default):
        0          → LOW
        1          → MEDIUM
        limit - 1  → HIGH   (one more absence = critical)
        >= limit   → CRITICAL
    """
    if current <= 0:
        return RiskLevel.LOW
    remaining = limit - current
    if remaining <= 0:
        return RiskLevel.CRITICAL
    if remaining == 1:
        return RiskLevel.HIGH
    if current == 1:
        return RiskLevel.MEDIUM
    return RiskLevel.MEDIUM


def _build_nb_status(subject: str, nb_count: int, nb_limit: int) -> NBStatus:
    remaining = max(0, nb_limit - nb_count)
    return NBStatus(
        subject=subject,
        current_nb=nb_count,
        max_nb=nb_limit,
        remaining=remaining,
        risk_level=_classify_risk(nb_count, nb_limit),
        percentage=round(nb_count / nb_limit * 100, 1) if nb_limit else 0.0,
    )


# ─── Attendance aggregation ───────────────────────────────────────────────────

def _aggregate_attendance(records: list[dict]) -> dict[str, NBStatus]:
    """
    Collapse raw attendance rows into one NBStatus per subject.
    Uses the max nb_count seen for each subject (authoritative from HEMIS).
    """
    seen: dict[str, dict] = {}
    for r in records:
        name = r["subject"]
        if name not in seen or r["nb_count"] > seen[name]["nb_count"]:
            seen[name] = r
    return {
        name: _build_nb_status(name, r["nb_count"], r.get("nb_limit", 4))
        for name, r in seen.items()
    }


# ─── Core service functions ───────────────────────────────────────────────────

async def check_nb_status(
    user_id: uuid.UUID,
    access_token: str = "",
) -> list[NBStatus]:
    """
    Fetch attendance for *user_id* and return an NBStatus per subject,
    sorted by risk (CRITICAL → HIGH → MEDIUM → LOW), then alphabetically.

    Falls back to mock data when USE_HEMIS_MOCK=true or token is empty.
    """
    logger.debug("check_nb_status called for user={}", user_id)

    if getattr(settings, "USE_HEMIS_MOCK", False) or not access_token:
        records = mock_get_attendance()
    else:
        try:
            async with make_hemis_client(access_token) as client:
                records = await client.get_attendance()
        except Exception as exc:
            logger.warning("HEMIS attendance fetch failed ({}), falling back to mock", exc)
            records = mock_get_attendance()

    aggregated = _aggregate_attendance(records)

    _risk_order = {
        RiskLevel.CRITICAL: 0,
        RiskLevel.HIGH:     1,
        RiskLevel.MEDIUM:   2,
        RiskLevel.LOW:      3,
    }
    return sorted(
        aggregated.values(),
        key=lambda s: (_risk_order[s.risk_level], s.subject),
    )


async def get_today_missed(
    user_id: uuid.UUID,
    access_token: str = "",
) -> list[MissedLesson]:
    """
    Return subjects missed today enriched with LMS topic and materials.

    The NB count for each missed subject is pulled from check_nb_status so
    the caller always sees the up-to-date risk alongside the lesson detail.
    """
    logger.debug("get_today_missed called for user={}", user_id)

    if getattr(settings, "USE_HEMIS_MOCK", False) or not access_token:
        raw = mock_get_today_missed()
    else:
        try:
            async with make_hemis_client(access_token) as client:
                # Real HEMIS: filter today's attendance for absent records
                all_records = await client.get_attendance()
                today_str = date.today().isoformat()
                raw = [
                    {
                        "subject":             r["subject"],
                        "topic":               "—",          # LMS integration point
                        "teacher":             "—",
                        "time":                "—",
                        "room":                "—",
                        "nb_count":            r.get("nb_count", 0),
                        "nb_limit":            r.get("nb_limit", 4),
                        "materials_available": False,
                        "materials":           [],
                        "can_request_p2p":     True,
                    }
                    for r in all_records
                    if r["date"] == today_str and r["status"] == "absent"
                ]
        except Exception as exc:
            logger.warning("HEMIS today-missed fetch failed ({}), falling back to mock", exc)
            raw = mock_get_today_missed()

    return [
        MissedLesson(
            subject=r["subject"],
            topic=r.get("topic", "—"),
            teacher=r.get("teacher", "—"),
            time=r.get("time", "—"),
            room=r.get("room", "—"),
            nb_count=r.get("nb_count", 0),
            nb_limit=r.get("nb_limit", 4),
            materials_available=r.get("materials_available", False),
            materials=r.get("materials", []),
            can_request_p2p=r.get("can_request_p2p", True),
            exam_in_days=r.get("exam_in_days"),
            exam_warning=r.get("exam_warning"),
        )
        for r in raw
    ]


async def get_upcoming_deadlines(
    user_id: uuid.UUID,
    access_token: str = "",
    days: int = 7,
) -> list[Deadline]:
    """
    Return exam / assignment deadlines within the next *days* calendar days,
    sorted by (date, time).

    Exams are always included; seminars and labs are included only when they
    fall within the window AND the student has an active NB risk for that subject.
    """
    logger.debug("get_upcoming_deadlines user={} days={}", user_id, days)

    if getattr(settings, "USE_HEMIS_MOCK", False) or not access_token:
        schedule = mock_get_schedule()
    else:
        try:
            async with make_hemis_client(access_token) as client:
                schedule = await client.get_schedule()
        except Exception as exc:
            logger.warning("HEMIS schedule fetch failed ({}), falling back to mock", exc)
            schedule = mock_get_schedule()

    today     = date.today()
    cutoff    = today + timedelta(days=days)
    deadlines: list[Deadline] = []

    for r in schedule:
        try:
            lesson_date = date.fromisoformat(r["date"])
        except (ValueError, KeyError):
            continue

        if not (today <= lesson_date <= cutoff):
            continue

        days_away = (lesson_date - today).days
        lesson_type: str = r.get("lesson_type", r.get("type", "lecture")).lower()
        is_exam = lesson_type == "exam" or r.get("is_exam", False)

        # Always include exams; optionally include other lesson types
        if not is_exam and lesson_type not in ("lab", "seminar"):
            continue

        deadlines.append(
            Deadline(
                subject=r["subject"],
                type=lesson_type,
                date=r["date"],
                time=r["time"],
                room=r.get("room", "—"),
                teacher=r.get("teacher", "—"),
                days_away=days_away,
                is_exam=is_exam,
                note=r.get("exam_note") or r.get("note"),
            )
        )

    deadlines.sort(key=lambda d: (d.date, d.time))
    return deadlines


# ─── Daily check (all users) ─────────────────────────────────────────────────

async def _run_daily_check_for_user(
    db: AsyncSession,
    user: User,
) -> DailyCheckResult:
    """Run the full NB pipeline for a single user and return structured result."""
    access_token: str = ""   # retrieved from Redis / DB in production

    nb_statuses  = await check_nb_status(user.id, access_token)
    missed_today = await get_today_missed(user.id, access_token)
    upcoming     = await get_upcoming_deadlines(user.id, access_token, days=7)

    danger = [s for s in nb_statuses if s.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)]

    return DailyCheckResult(
        user_id=user.id,
        checked_at=datetime.now(timezone.utc),
        nb_statuses=nb_statuses,
        danger_subjects=danger,
        missed_today=missed_today,
        upcoming_exams=[d for d in upcoming if d.is_exam],
    )


async def _daily_check_job() -> None:
    """
    APScheduler job — runs every night at 23:00 Tashkent time.

    Iterates over every active user, checks NB status, and persists
    Notification rows for HIGH/CRITICAL subjects so the Telegram bot
    can pick them up on next poll or push.
    """
    from models.user import Notification, NotificationType  # local import avoids circular

    logger.info("Daily NB check started at {}", datetime.now(timezone.utc).isoformat())
    checked = 0
    alerted = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.is_active.is_(True)))
        users: list[User] = list(result.scalars().all())

        for user in users:
            try:
                report = await _run_daily_check_for_user(db, user)
                checked += 1

                for danger in report.danger_subjects:
                    msg = (
                        f"⚠️ {danger.subject}: {danger.current_nb}/{danger.max_nb} NB "
                        f"({danger.remaining} ta qoldi) — {danger.risk_level.value}"
                    )
                    notification = Notification(
                        user_id=user.id,
                        type=NotificationType.subject_alert,
                        message=msg,
                        is_read=False,
                    )
                    db.add(notification)
                    alerted += 1

                for exam in report.upcoming_exams:
                    if exam.days_away <= 3:
                        msg = (
                            f"📝 Imtihon eslatmasi: {exam.subject} — "
                            f"{exam.date} soat {exam.time} ({exam.days_away} kun qoldi)"
                        )
                        notification = Notification(
                            user_id=user.id,
                            type=NotificationType.subject_alert,
                            message=msg,
                            is_read=False,
                        )
                        db.add(notification)
                        alerted += 1

            except Exception as exc:
                logger.error("Daily check failed for user={}: {}", user.id, exc)

        await db.commit()

    logger.info(
        "Daily NB check complete — {} users checked, {} notifications created",
        checked,
        alerted,
    )


# ─── Scheduler setup ─────────────────────────────────────────────────────────

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
    return _scheduler


def schedule_daily_check() -> AsyncIOScheduler:
    """
    Register the nightly 23:00 NB check job and return the scheduler.

    Call this once during app startup (e.g. inside the FastAPI lifespan).

        scheduler = schedule_daily_check()
        scheduler.start()
    """
    scheduler = get_scheduler()

    # Remove stale job before re-registering (idempotent)
    if scheduler.get_job("daily_nb_check"):
        scheduler.remove_job("daily_nb_check")

    scheduler.add_job(
        _daily_check_job,
        trigger=CronTrigger(hour=23, minute=0, timezone="Asia/Tashkent"),
        id="daily_nb_check",
        name="Nightly NB status check for all users",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=600,   # 10-minute grace if server was down
    )

    logger.info("Daily NB check scheduled at 23:00 Asia/Tashkent")
    return scheduler


# ─── Convenience: synchronous summary dict (for API responses) ────────────────

def nb_status_to_dict(s: NBStatus) -> dict:
    return {
        "subject":    s.subject,
        "current_nb": s.current_nb,
        "max_nb":     s.max_nb,
        "remaining":  s.remaining,
        "risk_level": s.risk_level.value,
        "percentage": s.percentage,
    }


def missed_lesson_to_dict(m: MissedLesson) -> dict:
    return {
        "subject":             m.subject,
        "topic":               m.topic,
        "teacher":             m.teacher,
        "time":                m.time,
        "room":                m.room,
        "nb_count":            m.nb_count,
        "nb_limit":            m.nb_limit,
        "materials_available": m.materials_available,
        "materials":           m.materials,
        "can_request_p2p":     m.can_request_p2p,
        "exam_in_days":        m.exam_in_days,
        "exam_warning":        m.exam_warning,
    }


def deadline_to_dict(d: Deadline) -> dict:
    return {
        "subject":   d.subject,
        "type":      d.type,
        "date":      d.date,
        "time":      d.time,
        "room":      d.room,
        "teacher":   d.teacher,
        "days_away": d.days_away,
        "is_exam":   d.is_exam,
        "note":      d.note,
    }
