"""
bot/config.py — Bot-specific configuration (extends core settings).
"""
from __future__ import annotations

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    BOT_TOKEN: str = ""
    WEBSITE_URL: str = "https://edumentor.ai"

    # Re-expose what the bot needs from the main config
    HEMIS_CLIENT_ID: str = ""
    HEMIS_CLIENT_SECRET: str = ""
    HEMIS_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/hemis/callback"
    USE_HEMIS_MOCK: bool = True

    REDIS_URL: str = "redis://localhost:6379/0"

    # FSM storage backend: "memory" | "redis"
    FSM_STORAGE: str = "redis"


bot_settings = BotSettings()
