import json
from typing import Any
import redis.asyncio as aioredis

from core.config import settings


class CacheService:
    def __init__(self, redis: aioredis.Redis):
        self.redis = redis
        self.default_ttl = 300  # 5 minutes

    async def get(self, key: str) -> Any | None:
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        await self.redis.setex(
            key,
            ttl or self.default_ttl,
            json.dumps(value, default=str),
        )

    async def delete(self, key: str) -> None:
        await self.redis.delete(key)

    async def delete_pattern(self, pattern: str) -> None:
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)

    def make_key(self, *parts: str) -> str:
        return ":".join(["sezgi", *parts])
