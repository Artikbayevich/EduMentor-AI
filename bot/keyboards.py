"""
bot/keyboards.py — All inline and reply keyboards.
"""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


# ─── Auth ─────────────────────────────────────────────────────────────────────

def hemis_login_keyboard(auth_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎓 HEMIS orqali kirish", url=auth_url)
    builder.button(text="❓ Yordam",              callback_data="help")
    builder.adjust(1)
    return builder.as_markup()


def already_logged_in_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Status",          callback_data="cmd_status")
    builder.button(text="📅 Deadlines",       callback_data="cmd_deadlines")
    builder.button(text="⚠️ NB holati",       callback_data="cmd_nb")
    builder.button(text="🔄 Qayta ulash",     callback_data="relogin")
    builder.adjust(2)
    return builder.as_markup()


# ─── Main menu (persistent reply keyboard) ────────────────────────────────────

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="📊 Status")
    builder.button(text="📅 Deadlines")
    builder.button(text="⚠️ NB holati")
    builder.button(text="🤝 P2P yordam")
    builder.button(text="🏆 Reyting")
    builder.button(text="❓ Yordam")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


# ─── NB detail ────────────────────────────────────────────────────────────────

def nb_detail_keyboard(subject: str, lesson_id: str, website_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📖 Konspekt va testni ko'rish",
        url=f"{website_url}/lesson/{lesson_id}",
    )
    builder.button(
        text="🤝 P2P yordam so'rash",
        callback_data=f"p2p_request:{subject}",
    )
    builder.adjust(1)
    return builder.as_markup()


def missed_lesson_keyboard(subject: str, lesson_id: str, website_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📚 Materiallarni ko'rish",
        url=f"{website_url}/lesson/{lesson_id}",
    )
    builder.button(
        text="📝 Test ishlash",
        url=f"{website_url}/lesson/{lesson_id}/test",
    )
    builder.button(
        text="🤝 Mentor topish",
        callback_data=f"p2p_request:{subject}",
    )
    builder.adjust(2, 1)
    return builder.as_markup()


# ─── Schedule / deadline navigation ──────────────────────────────────────────

def deadline_keyboard(website_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🌐 To'liq jadval", url=f"{website_url}/schedule")
    builder.button(text="🔔 Eslatmani yoqish", callback_data="toggle_reminders")
    builder.adjust(1)
    return builder.as_markup()


# ─── P2P ─────────────────────────────────────────────────────────────────────

def p2p_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Yuborish",   callback_data="p2p_confirm")
    builder.button(text="❌ Bekor qilish", callback_data="p2p_cancel")
    builder.adjust(2)
    return builder.as_markup()


def p2p_accept_keyboard(request_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Qabul qilish", callback_data=f"p2p_accept:{request_id}")
    builder.button(text="❌ Rad etish",    callback_data=f"p2p_reject:{request_id}")
    builder.adjust(2)
    return builder.as_markup()


# ─── Misc ─────────────────────────────────────────────────────────────────────

def cancel_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Bekor qilish")
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


remove_keyboard = ReplyKeyboardRemove()
