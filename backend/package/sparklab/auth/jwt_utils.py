from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

from sparklab.config import get_settings
from sparklab.storage.redis import get_redis

BLACKLIST_PREFIX = "blacklist:"


def create_access_token(
    user_id: int,
    role: str,
    expires_delta: timedelta | None = None,
) -> tuple[str, str, datetime]:
    settings = get_settings()
    jti = uuid4().hex
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))

    payload = {
        "jti": jti,
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, jti, expire


def decode_access_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": True},
        )
        return payload
    except jwt.PyJWTError:
        return None


async def blacklist_token(jti: str, expires_in_seconds: int) -> None:
    redis = get_redis()
    await redis.setex(f"{BLACKLIST_PREFIX}{jti}", expires_in_seconds, "1")


async def is_token_blacklisted(jti: str) -> bool:
    redis = get_redis()
    result = await redis.exists(f"{BLACKLIST_PREFIX}{jti}")
    return result > 0
