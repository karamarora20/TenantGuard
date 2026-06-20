import redis.asyncio as aioredis
from src.config.settings import settings
import asyncio

_redis: aioredis.Redis | None = None


async def init_redis():
    global _redis
    _redis = await aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


async def close_redis():
    if _redis:
        await _redis.close()


def get_redis() -> aioredis.Redis:
    if not _redis:
        raise RuntimeError("Redis pool not initialised — call init_redis() at startup")
    return _redis

