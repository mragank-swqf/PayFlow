from app.core.redis import get_redis

IDEMPOTENCY_KEY_PREFIX = "idempotency:"


async def check_idempotency_key(key: str) -> str | None:
    redis = await get_redis()
    return await redis.get(f"{IDEMPOTENCY_KEY_PREFIX}{key}")