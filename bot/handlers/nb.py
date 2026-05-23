"""
bot/handlers/nb.py — /nb command: per-subject NB status with risk indicators.
"""
from __future__ import annotations

import uuid

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.config import bot_settings
from bot.messages import NOT_AUTHENTICATED, format_nb_list, format_nb_alert
from bot.keyboards import nb_detail_keyboard
from bot.states import AuthStates
from services.nb_service import check_nb_status, get_today_missed, RiskLevel
from loguru import logger

router = Router(name="nb")


async def _send_nb(target: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current != AuthStates.authenticated.state:
        await target.answer(NOT_AUTHENTICATED, parse_mode="HTML")
        return

    data         = await state.get_data()
    user_id_str  = data.get("user_id")
    access_token = data.get("access_token", "")

    user_id = uuid.UUID(user_id_str) if user_id_str else None

    await target.answer("⏳ NB ma'lumotlari yuklanmoqda...")

    nb_statuses = await check_nb_status(user_id, access_token) if user_id else []

    text = format_nb_list(nb_statuses, bot_settings.WEBSITE_URL)
    await target.answer(text, parse_mode="HTML", disable_web_page_preview=True)

    # Send individual alerts for HIGH / CRITICAL subjects
    missed = await get_today_missed(user_id, access_token) if user_id else []
    for lesson in missed:
        if lesson.nb_count >= 2:   # only alert for genuinely risky subjects
            lesson_id = f"{lesson.subject.lower().replace(' ', '-')}-latest"
            alert_text = format_nb_alert(
                missed=lesson,
                website_url=bot_settings.WEBSITE_URL,
                lesson_id=lesson_id,
            )
            await target.answer(
                alert_text,
                parse_mode="HTML",
                reply_markup=nb_detail_keyboard(
                    subject=lesson.subject,
                    lesson_id=lesson_id,
                    website_url=bot_settings.WEBSITE_URL,
                ),
                disable_web_page_preview=False,
            )


@router.message(Command("nb"))
@router.message(F.text == "⚠️ NB holati")
async def cmd_nb(message: Message, state: FSMContext) -> None:
    await _send_nb(message, state)


@router.callback_query(F.data == "cmd_nb")
async def cb_nb(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _send_nb(callback.message, state)


# ── Proactive notification (called by nb_service nightly job) ────────────────

async def send_nb_alert(
    bot,
    telegram_id: int,
    missed_lesson,          # MissedLesson dataclass
    website_url: str,
) -> None:
    """
    Push a proactive NB alert to a specific user.
    Called from the APScheduler daily check, NOT from user interaction.
    """
    lesson_id = f"{missed_lesson.subject.lower().replace(' ', '-')}-latest"
    text = format_nb_alert(missed_lesson, website_url, lesson_id)
    try:
        await bot.send_message(
            telegram_id,
            text,
            parse_mode="HTML",
            reply_markup=nb_detail_keyboard(
                subject=missed_lesson.subject,
                lesson_id=lesson_id,
                website_url=website_url,
            ),
        )
        logger.info("NB alert sent to tg_uid={} subject={}", telegram_id, missed_lesson.subject)
    except Exception as exc:
        logger.error("Failed to send NB alert to tg_uid={}: {}", telegram_id, exc)
