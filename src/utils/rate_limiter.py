import time
from src.db.redis import get_redis
from src.config.settings import settings

WINDOW_SECONDS = 60


async def is_rate_limited(tenant_id: str, plan: str) -> tuple[bool, int]:
    """
    Returns (is_limited, retry_after_seconds).

    retry_after_seconds is 0 if not limited, or the number of seconds
    until the oldest request in the window falls out and a slot opens.
    """
    limit = settings.rate_limits.get(plan, settings.rate_limits["free"])
    redis = get_redis()
    key = f"ratelimit:{tenant_id}"
    now = time.time()
    window_start = now - WINDOW_SECONDS

    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, "-inf", window_start)
    pipe.zcard(key)
    pipe.zadd(key, {str(now): now})
    # Set expiry so idle keys don't accumulate in Redis
    pipe.expire(key, WINDOW_SECONDS)
    results = await pipe.execute()

    current_count = results[1]  # count BEFORE adding this request

    if current_count >= limit:
        # Find oldest request in window — its expiry is when a slot opens
        oldest = await redis.zrange(key, 0, 0, withscores=True)
        if oldest:
            oldest_timestamp = oldest[0][1]
            retry_after = int(oldest_timestamp + WINDOW_SECONDS - now) + 1
        else:
            retry_after = WINDOW_SECONDS
        return True, retry_after

    return False, 0