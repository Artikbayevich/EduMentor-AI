"""
bot/notification_scheduler.py — APScheduler jobs for EduMentor AI bot.

Jobs:
  • daily_nb_check()    — 23:30  Asia/Tashkent  (new NB detection)
  • deadline_reminder() — 08:00  Asia/Tashkent  (exams in ≤3 days)
  • weekly_summary()    — Monday 09:00 Asia/Tashkent

All Telegram messages are short with a website deep-link.
No study content is sent via the bot.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

if TYPE_CHECKING:
    from aiogram import Bot

# ─── Timezone ─────────────────────────────────────────────────────────────────

_TZ = "Asia/Tashkent"

# ─── Message builders ─────────────────────────────────────────────────────────

def _nb_alert_msg(subject: str, nb_count: int, nb_limit: int, lesson_id: str, website_url: str) -> str:
    remaining = nb_limit - nb_count
    risk_icon  = "🔴" if remaining <= 1 else "🟠"
    return (
        f"⚠️ <b>{subject}</b> fanida yangi NB qayd etildi\n\n"
        f"📊 NB holati: {nb_count}/{nb_limit} "
        f"({risk_icon} {remaining} ta qoldi)\n\n"
        f"→ Dars materiallarini ko'rish:\n"
        f"{website_url}/lesson/{lesson_id}"
    )


def _deadline_msg(subject: str, lesson_type: str, days_away: int, schedule_url: str) -> str:
    urgency  = "❗" if days_away <= 1 else ("⚡" if days_away <= 2 else "📅")
    days_txt = "Bugun!" if days_away == 0 else f"{days_away} kun qoldi"
    type_map  = {
        "exam":     "Imtihon",
        "lab":      "Laboratoriya",
        "seminar":  "Seminar",
        "practice": "Amaliyot",
    }
    type_label = type_map.get(lesson_type.lower(), lesson_type.capitalize())
    return (
        f"{urgency} <b>{subject}</b>: {type_label} — {days_txt}\n"
        f"→ {schedule_url}"
    )


def _weekly_summary_msg(
    full_name: str,
    attendance_pct: float,
    coin_balance: float,
    rank_university: int | None,
    rank_national: int | None,
    website_url: str,
) -> str:
    attend_icon = "✅" if attendance_pct >= 85 else ("⚠️" if attendance_pct >= 70 else "🔴")
    return (
        f"📊 <b>Haftalik hisobot</b> — {full_name}\n\n"
        f"{attend_icon} Davomat: <b>{attendance_pct:.1f}%</b>\n"
        f"💰 Coin balansi: <b>{coin_balance:.0f}</b>\n"
        f"🏫 Universitet reytingi: <b>#{rank_university or '—'}</b>\n"
        f"🇺🇿 Milliy reyting: <b>#{rank_national or '—'}</b>\n\n"
        f"→ To'liq statistika: {website_url}/dashboard"
    )


# ─── Job implementations ──────────────────────────────────────────────────────

async def daily_nb_check(bot: "Bot", website_url: str) -> None:
    """
    23:30 — Scan every active, authenticated user for new absences.
    Sends a Telegram alert for each subject where NB count increased
    since the last recorded check.
    """
    logger.info("JOB daily_nb_check started at {}", datetime.now(timezone.utc).isoformat())

    from core.database import AsyncSessionLocal
    from sqlalchemy import select
    from models.user import User, Notification, NotificationType
    from services.nb_service import check_nb_status, get_today_missed, RiskLevel
    from services.hemis.hemis_mock import mock_get_attendance   # swap when real tokens ready

    sent = skipped = errors = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.is_active.is_(True), User.telegram_id.isnot(None))
        )
        users: list[User] = list(result.scalars().all())
        logger.debug("daily_nb_check: {} active users with Telegram", len(users))

        for user in users:
            try:
                # Retrieve NB statuses (mock or real)
                nb_statuses = await check_nb_status(user.id, access_token="")
                missed_today = await get_today_missed(user.id, access_token="")

                for missed in missed_today:
                    # Only alert on genuinely risky absences
                    if missed.nb_count < 1:
                        continue

                    lesson_id = missed.subject.lower().replace(" ", "-") + "-latest"
                    text = _nb_alert_msg(
                        subject=missed.subject,
                        nb_count=missed.nb_count,
                        nb_limit=missed.nb_limit,
                        lesson_id=lesson_id,
                        website_url=website_url,
                    )

                    try:
                        await bot.send_message(
                            user.telegram_id,
                            text,
                            parse_mode="HTML",
                            disable_web_page_preview=False,
                        )
                        sent += 1

                        # Persist notification record
                        db.add(Notification(
                            user_id=user.id,
                            type=NotificationType.subject_alert,
                            message=text,
                            is_read=False,
                        ))
                    except Exception as send_exc:
                        logger.warning(
                            "daily_nb_check: send failed uid={} tg={}: {}",
                            user.id, user.telegram_id, send_exc,
                        )
                        skipped += 1

            except Exception as exc:
                logger.error("daily_nb_check: error for user={}: {}", user.id, exc)
                errors += 1

        await db.commit()

    logger.info(
        "daily_nb_check done — sent={} skipped={} errors={}",
        sent, skipped, errors,
    )


async def deadline_reminder(bot: "Bot", website_url: str) -> None:
    """
    08:00 — Remind users about exams / labs / seminars in ≤3 days.
    One message per upcoming deadline.
    """
    logger.info("JOB deadline_reminder started at {}", datetime.now(timezone.utc).isoformat())

    from core.database import AsyncSessionLocal
    from sqlalchemy import select
    from models.user import User, Notification, NotificationType
    from services.nb_service import get_upcoming_deadlines

    sent = skipped = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.is_active.is_(True), User.telegram_id.isnot(None))
        )
        users: list[User] = list(result.scalars().all())

        for user in users:
            try:
                deadlines = await get_upcoming_deadlines(
                    user.id, access_token="", days=3
                )
                if not deadlines:
                    continue

                for dl in deadlines:
                    if dl.days_away > 3:
                        continue

                    schedule_url = f"{website_url}/schedule?subject={dl.subject.replace(' ', '+')}"
                    text = _deadline_msg(
                        subject=dl.subject,
                        lesson_type=dl.type,
                        days_away=dl.days_away,
                        schedule_url=schedule_url,
                    )

                    try:
                        await bot.send_message(
                            user.telegram_id,
                            text,
                            parse_mode="HTML",
                            disable_web_page_preview=True,
                        )
                        sent += 1

                        db.add(Notification(
                            user_id=user.id,
                            type=NotificationType.subject_alert,
                            message=text,
                            is_read=False,
                        ))
                    except Exception as send_exc:
                        logger.warning(
                            "deadline_reminder: send failed uid={} tg={}: {}",
                            user.id, user.telegram_id, send_exc,
                        )
                        skipped += 1

            except Exception as exc:
                logger.error("deadline_reminder: error for user={}: {}", user.id, exc)

        await db.commit()

    logger.info("deadline_reminder done — sent={} skipped={}", sent, skipped)


async def weekly_summary(bot: "Bot", website_url: str) -> None:
    """
    Monday 09:00 — Send each user their weekly attendance %, coin balance,
    and leaderboard rank. One message per user, link to dashboard.
    """
    logger.info("JOB weekly_summary started at {}", datetime.now(timezone.utc).isoformat())

    from core.database import AsyncSessionLocal
    from sqlalchemy import select
    from models.user import User, LeaderboardEntry
    from services.nb_service import check_nb_status

    sent = skipped = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.is_active.is_(True), User.telegram_id.isnot(None))
        )
        users: list[User] = list(result.scalars().all())

        # Fetch all leaderboard entries in one query
        lb_result = await db.execute(select(LeaderboardEntry))
        lb_map: dict[uuid.UUID, LeaderboardEntry] = {
            e.user_id: e for e in lb_result.scalars().all()
        }

        for user in users:
            try:
                # Attendance percentage from NB data
                nb_statuses = await check_nb_status(user.id, access_token="")
                total_nb    = sum(s.current_nb for s in nb_statuses)
                total_max   = sum(s.max_nb     for s in nb_statuses) or 1
                # Attendance % inverse of absence ratio
                attendance_pct = max(0.0, (1 - total_nb / (total_max * 4)) * 100)

                lb = lb_map.get(user.id)
                text = _weekly_summary_msg(
                    full_name=user.full_name,
                    attendance_pct=attendance_pct,
                    coin_balance=float(user.coin_balance or 0),
                    rank_university=lb.rank_university if lb else None,
                    rank_national=lb.rank_national   if lb else None,
                    website_url=website_url,
                )

                try:
                    await bot.send_message(
                        user.telegram_id,
                        text,
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )
                    sent += 1
                except Exception as send_exc:
                    logger.warning(
                        "weekly_summary: send failed uid={} tg={}: {}",
                        user.id, user.telegram_id, send_exc,
                    )
                    skipped += 1

            except Exception as exc:
                logger.error("weekly_summary: error for user={}: {}", user.id, exc)

    logger.info("weekly_summary done — sent={} skipped={}", sent, skipped)


# ─── Scheduler factory ────────────────────────────────────────────────────────

def create_notification_scheduler(bot: "Bot", website_url: str) -> AsyncIOScheduler:
    """
    Build and return a fully configured AsyncIOScheduler.

    Call scheduler.start() after the event loop is running
    (e.g. inside the FastAPI lifespan or aiogram on_startup hook).

    Jobs are registered with replace_existing=True so hot-reloading
    the scheduler is safe.
    """
    scheduler = AsyncIOScheduler(timezone=_TZ)

    # ── 1. Daily NB check — 23:30 ────────────────────────────────────────────
    scheduler.add_job(
        daily_nb_check,
        trigger=CronTrigger(hour=23, minute=30, timezone=_TZ),
        id="daily_nb_check",
        name="Daily NB absence check",
        kwargs={"bot": bot, "website_url": website_url},
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=300,   # 5-min grace if server was briefly down
    )

    # ── 2. Deadline reminder — 08:00 ──────────────────────────────────────────
    scheduler.add_job(
        deadline_reminder,
        trigger=CronTrigger(hour=8, minute=0, timezone=_TZ),
        id="deadline_reminder",
        name="Morning deadline reminder",
        kwargs={"bot": bot, "website_url": website_url},
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=600,   # 10-min grace
    )

    # ── 3. Weekly summary — Monday 09:00 ──────────────────────────────────────
    scheduler.add_job(
        weekly_summary,
        trigger=CronTrigger(day_of_week="mon", hour=9, minute=0, timezone=_TZ),
        id="weekly_summary",
        name="Weekly student summary",
        kwargs={"bot": bot, "website_url": website_url},
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=1800,  # 30-min grace (weekly is less time-sensitive)
    )

    logger.info(
        "Notification scheduler configured — 3 jobs: "
        "nb_check@23:30, deadline@08:00, weekly_summary@Mon09:00 [{}]",
        _TZ,
    )
    return scheduler


# ─── Convenience: get next fire times (useful for /admin status) ─────────────

def get_job_schedule(scheduler: AsyncIOScheduler) -> list[dict]:
    """Return human-readable next-run info for all registered jobs."""
    jobs = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        jobs.append({
            "id":       job.id,
            "name":     job.name,
            "next_run": next_run.isoformat() if next_run else "paused",
        })
    return jobs
