"""
bot/handlers/status.py — /status command: today's schedule + NB summary.
"""
from __future__ import annotations

from datetime import date

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.config import bot_settings
from bot.messages import NOT_AUTHENTICATED, format_status
from bot.keyboards import deadline_keyboard
from bot.states import AuthStates
from services.nb_service import check_nb_status
from services.hemis.hemis_mock import mock_get_schedule
from loguru import logger

router = Router(name="status")


async def _send_status(target: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current != AuthStates.authenticated.state:
        await target.answer(NOT_AUTHENTICATED, parse_mode="HTML")
        return

    data        = await state.get_data()
    full_name   = data.get("full_name", "Foydalanuvchi")
    user_id     = data.get("user_id")
    access_token= data.get("access_token", "")

    await target.answer("⏳ Ma'lumotlar yuklanmoqda...")

    # Today's schedule (filter to today's date)
    today_str = date.today().isoformat()
    all_schedule = mock_get_schedule()   # swap for real client when token available
    today_schedule = [
        r for r in all_schedule if r["date"] == today_str
    ]

    # NB statuses
    nb_statuses = await check_nb_status(user_id, access_token) if user_id else []

    text = format_status(
        full_name=full_name,
        today_schedule=today_schedule,
        nb_statuses=nb_statuses,
        website_url=bot_settings.WEBSITE_URL,
    )
    await target.answer(
        text,
        parse_mode="HTML",
        reply_markup=deadline_keyboard(bot_settings.WEBSITE_URL),
        disable_web_page_preview=True,
    )


@router.message(Command("status"))
@router.message(F.text == "📊 Status")
async def cmd_status(message: Message, state: FSMContext) -> None:
    await _send_status(message, state)


@router.callback_query(F.data == "cmd_status")
async def cb_status(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _send_status(callback.message, state)
