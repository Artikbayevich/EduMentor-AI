"""
bot/main.py — Sezgi Telegram bot entry point.

Run standalone:
    python -m bot.main

Or alongside the FastAPI server (recommended):
    Use asyncio.gather() in a launcher script — see README.

Architecture:
  • aiogram 3.x with AsyncIO event loop
  • FSM storage: Redis (falls back to memory if Redis unavailable)
  • Middlewares: LoggingMiddleware, AuthCheckMiddleware
  • All handlers registered via bot/handlers/__init__.py
"""
from __future__ import annotations

import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger

from bot.config import bot_settings
from bot.handlers import all_routers
from bot.middlewares import LoggingMiddleware, AuthCheckMiddleware
from bot.notification_scheduler import create_notification_scheduler, get_job_schedule

# Module-level scheduler reference (shared between hooks)
_notification_scheduler = None


# ─── Bot & dispatcher factory ─────────────────────────────────────────────────

def create_bot() -> Bot:
    if not bot_settings.BOT_TOKEN:
        logger.critical("BOT_TOKEN is not set. Add it to your .env file.")
        sys.exit(1)

    return Bot(
        token=bot_settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    # FSM storage
    if bot_settings.FSM_STORAGE == "redis":
        try:
            from redis.asyncio import Redis as AIORedis
            redis = AIORedis.from_url(bot_settings.REDIS_URL)
            storage = RedisStorage(redis=redis)
            logger.info("FSM storage: Redis ({})", bot_settings.REDIS_URL)
        except Exception as exc:
            logger.warning("Redis unavailable ({}), falling back to MemoryStorage.", exc)
            storage = MemoryStorage()
    else:
        storage = MemoryStorage()
        logger.info("FSM storage: Memory")

    dp = Dispatcher(storage=storage)

    # Middlewares (applied to all update types)
    dp.update.middleware(LoggingMiddleware())
    dp.update.middleware(AuthCheckMiddleware())

    # Register all routers
    for router in all_routers:
        dp.include_router(router)
        logger.debug("Router registered: {}", router.name)

    return dp


# ─── Startup / shutdown hooks ─────────────────────────────────────────────────

async def on_startup(bot: Bot) -> None:
    global _notification_scheduler
    from aiogram.types import BotCommand

    await bot.set_my_commands([
        BotCommand(command="start",     description="Botni ishga tushirish / kirish"),
        BotCommand(command="status",    description="Bugungi jadval va NB holati"),
        BotCommand(command="nb",        description="Fan bo'yicha NB holati"),
        BotCommand(command="deadlines", description="Yaqin 7 kunlik imtihonlar"),
        BotCommand(command="help",      description="Yordam"),
    ])

    # Start notification scheduler
    _notification_scheduler = create_notification_scheduler(
        bot=bot,
        website_url=bot_settings.WEBSITE_URL,
    )
    _notification_scheduler.start()
    upcoming = get_job_schedule(_notification_scheduler)
    for job in upcoming:
        logger.info("Scheduled: {} → next run: {}", job["name"], job["next_run"])

    me = await bot.get_me()
    logger.info("Bot started: @{} (id={})", me.username, me.id)


async def on_shutdown(bot: Bot) -> None:
    global _notification_scheduler
    logger.info("Bot shutting down...")
    if _notification_scheduler and _notification_scheduler.running:
        _notification_scheduler.shutdown(wait=False)
        logger.info("Notification scheduler stopped.")
    await bot.session.close()


# ─── Main coroutine ───────────────────────────────────────────────────────────

async def main() -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
        level="DEBUG",
        colorize=True,
    )
    logger.add(
        "logs/bot.log",
        rotation="10 MB",
        retention="7 days",
        level="INFO",
    )

    bot = create_bot()
    dp  = create_dispatcher()

    # Register lifecycle hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("Starting polling...")
    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
