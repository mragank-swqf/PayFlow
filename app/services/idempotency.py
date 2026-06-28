from app.core.redis import get_redis
import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency import IdempotencyKey

IDEMPOTENCY_KEY_PREFIX = "idempotency:"


async def check_idempotency_key(key: str) -> str | None:
    redis = await get_redis()
    return await redis.get(f"{IDEMPOTENCY_KEY_PREFIX}{key}")


async def store_idempotency_key(
    key: str,
    response: dict,
    db: AsyncSession,
    transaction_id: uuid.UUID | None = None,
    ttl: int = 86400,
) -> None:
    snapshot = json.dumps(response, default=str)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

    redis = await get_redis()
    await redis.set(f"{IDEMPOTENCY_KEY_PREFIX}{key}", snapshot, ex=ttl)

    record = IdempotencyKey(
        key=key,
        transaction_id=transaction_id,
        response_snapshot=snapshot,
        expires_at=expires_at,
    )
    db.add(record)