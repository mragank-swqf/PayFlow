from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.services.auth import decode_access_token

import json
import uuid
from fastapi import Header
from app.services.idempotency import IdempotencyContext, check_idempotency_key

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    return user

async def require_idempotency_key(
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> IdempotencyContext:
    try:
        uuid.UUID(idempotency_key, version=4)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Idempotency-Key must be a valid UUID v4",
        )

    cached = await check_idempotency_key(idempotency_key)
    if cached is not None:
        return IdempotencyContext(
            key=idempotency_key,
            cached_response=json.loads(cached),
        )

    return IdempotencyContext(key=idempotency_key)