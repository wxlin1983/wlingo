from datetime import datetime, timedelta

from fastapi import Cookie, Depends
from pydantic import ValidationError

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
    try:
        session = SessionData.model_validate_json(raw)
    except ValidationError:
        # Corrupt/incompatible payload (e.g. after a model change) — drop it
        # rather than 500ing, and treat it as if there's no active session.
        redis.delete(session_id)
        return None
    # Belt-and-suspenders alongside the Redis TTL; cleans up stale data on access
    if datetime.now() - session.created_at > timedelta(
        minutes=settings.SESSION_TIMEOUT_MINUTES
    ):
        redis.delete(session_id)
        return None
    return session
