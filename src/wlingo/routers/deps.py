from datetime import datetime, timedelta

from fastapi import Cookie, Depends

from ..config import settings
from ..models import SessionData
from ..redis_session import redis_client as _redis_client


def get_redis():
    return _redis_client


def get_session_id(
    session_id: str | None = Cookie(None, alias=settings.SESSION_COOKIE_NAME),
) -> str | None:
    return session_id


def get_user_id(
    user_id: str | None = Cookie(None, alias=settings.USER_COOKIE_NAME),
) -> str | None:
    return user_id


def get_active_session(
    session_id: str | None = Depends(get_session_id),
    redis=Depends(get_redis),
) -> SessionData | None:
    if not session_id:
        return None
    raw = redis.get(session_id)
    if not raw:
        return None
    session = SessionData.model_validate_json(raw)
    # Belt-and-suspenders alongside the Redis TTL; cleans up stale data on access
    if datetime.now() - session.created_at > timedelta(minutes=settings.SESSION_TIMEOUT_MINUTES):
        redis.delete(session_id)
        return None
    return session
