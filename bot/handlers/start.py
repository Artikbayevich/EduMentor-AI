"""
bot/handlers/start.py — /start command and HEMIS OAuth2 auth flow.
"""
from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.config import bot_settings
from bot.states import AuthStates
from bot.keyboards import hemis_login_keyboard, already_logged_in_keyboard, main_menu_keyboard
from bot.messages import WELCOME, ALREADY_LOGGED_IN, AUTH_PENDING, NOT_AUTHENTICATED, HELP
from services.hemis.hemis_auth import get_auth_url
from loguru import logger

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, is_authenticated: bool) -> None:
    if is_authenticated:
        data = await state.get_data()
        full_name = data.get("full_name", "Foydalanuvchi")
        await message.answer(
            f"✅ Xush kelibsiz, <b>{full_name}</b>!\n\n" + ALREADY_LOGGED_IN,
            reply_markup=already_logged_in_keyboard(),
            parse_mode="HTML",
        )
        return

    # Build HEMIS OAuth URL — use telegram_id as state to bind the session
    import secrets
    oauth_state = f"tg_{message.from_user.id}_{secrets.token_hex(8)}"
    auth_url, _, verifier = get_auth_url(
        redirect_uri=bot_settings.HEMIS_REDIRECT_URI,
        state=oauth_state,
        use_pkce=True,
    )

    # Persist verifier + state so the callback endpoint can verify
    await state.update_data(
        oauth_state=oauth_state,
        code_verifier=verifier,
        telegram_id=message.from_user.id,
    )
    await state.set_state(AuthStates.waiting_for_hemis)

    await message.answer(
        WELCOME,
        reply_markup=hemis_login_keyboard(auth_url),
        parse_mode="HTML",
    )
    logger.info("OAuth flow started for tg_uid={}", message.from_user.id)


@router.message(Command("help"))
@router.callback_query(F.data == "help")
async def cmd_help(event: Message | CallbackQuery, **_) -> None:
    text = HELP.format(website_url=bot_settings.WEBSITE_URL)
    if isinstance(event, CallbackQuery):
        await event.message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML", disable_web_page_preview=True)


@router.callback_query(F.data == "relogin")
async def cb_relogin(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("🔄 Qayta kirish uchun /start ni bosing.")
    await callback.answer()


# ── Called by the FastAPI OAuth callback endpoint ────────────────────────────

async def complete_auth(
    bot,
    telegram_id: int,
    state: FSMContext,
    user_data: dict,
) -> None:
    """
    Finalise authentication after the FastAPI /hemis/callback endpoint
    verifies the token and fetches student info from HEMIS.

    Called externally (not by aiogram router) — hence not a handler.
    """
    await state.update_data(**user_data)
    await state.set_state(AuthStates.authenticated)

    from bot.messages import AUTH_SUCCESS
    text = AUTH_SUCCESS.format(
        full_name=user_data.get("full_name", ""),
        university=user_data.get("university", ""),
        faculty=user_data.get("faculty", ""),
        course=user_data.get("course", ""),
    )
    await bot.send_message(
        telegram_id,
        text,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )
    logger.info("Auth completed for tg_uid={}", telegram_id)
