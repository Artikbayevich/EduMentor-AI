"""
bot/handlers/deadlines.py — /deadlines command: next 7 days exams/labs.
"""
from __future__ import annotations

import uuid

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.config import bot_settings
from bot.messages import NOT_AUTHENTICATED, format_deadlines
from bot.keyboards import deadline_keyboard
from bot.states import AuthStates
from services.nb_service import get_upcoming_deadlines

router = Router(name="deadlines")


async def _send_deadlines(target: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current != AuthStates.authenticated.state:
        await target.answer(NOT_AUTHENTICATED, parse_mode="HTML")
        return

    data         = await state.get_data()
    user_id_str  = data.get("user_id")
    access_token = data.get("access_token", "")
    user_id      = uuid.UUID(user_id_str) if user_id_str else None

    await target.answer("⏳ Jadval yuklanmoqda...")

    deadlines = await get_upcoming_deadlines(user_id, access_token, days=7) if user_id else []

    text = format_deadlines(deadlines, bot_settings.WEBSITE_URL)
    await target.answer(
        text,
        parse_mode="HTML",
        reply_markup=deadline_keyboard(bot_settings.WEBSITE_URL),
        disable_web_page_preview=True,
    )


@router.message(Command("deadlines"))
@router.message(F.text == "📅 Deadlines")
async def cmd_deadlines(message: Message, state: FSMContext) -> None:
    await _send_deadlines(message, state)


@router.callback_query(F.data == "cmd_deadlines")
async def cb_deadlines(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _send_deadlines(callback.message, state)


@router.callback_query(F.data == "toggle_reminders")
async def cb_toggle_reminders(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    reminders_on = data.get("reminders_enabled", True)
    new_state = not reminders_on
    await state.update_data(reminders_enabled=new_state)
    status = "yoqildi ✅" if new_state else "o'chirildi 🔕"
    await callback.answer(f"Eslatmalar {status}", show_alert=True)
