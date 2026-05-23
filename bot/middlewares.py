"""
bot/middlewares.py — aiogram 3.x middlewares.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from loguru import logger


class LoggingMiddleware(BaseMiddleware):
    """Logs every incoming update (user, type, text)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Update):
            if event.message:
                user = event.message.from_user
                logger.debug(
                    "MSG  | uid={} | @{} | {}",
                    user.id if user else "?",
                    user.username if user else "?",
                    (event.message.text or "")[:80],
                )
            elif event.callback_query:
                user = event.callback_query.from_user
                logger.debug(
                    "CBQ  | uid={} | @{} | data={}",
                    user.id,
                    user.username,
                    event.callback_query.data,
                )
        return await handler(event, data)


class AuthCheckMiddleware(BaseMiddleware):
    """
    Injects `is_authenticated` bool into handler data.

    Does NOT block unauthenticated users — handlers decide themselves
    so that /start always passes through.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # FSM state is already in data["state"] at this point
        state = data.get("state")
        current = await state.get_state() if state else None

        from bot.states import AuthStates
        data["is_authenticated"] = current == AuthStates.authenticated.state
        return await handler(event, data)
