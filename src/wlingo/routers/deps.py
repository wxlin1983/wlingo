import uuid
from datetime import UTC, datetime, timedelta

from fastapi import Cookie, Depends
from pydantic import ValidationError
from redis import Redis

from ..config import settings
from ..models import SessionData
from ..redis_session import redis_client as _redis_client


def get_redis() -> Redis:
    return _redis_client


def session_key(session_id: str) -> str:
    return f"session:{session_id}"


def get_session_id(
    session_id: str | None = Cookie(None, alias=settings.SESSION_COOKIE_NAME),
) -> str | None:
    return session_id


def get_user_id(
    user_id: str | None = Cookie(None, alias=settings.USER_COOKIE_NAME),
) -> str | None:
    # The cookie is client-supplied and becomes part of a Redis key — accept
    # only well-formed UUIDs so arbitrary values can't mint junk keys.
    if user_id is None:
        return None
    try:
        uuid.UUID(user_id)
    except ValueError:
        return None
    return user_id


def get_active_session(
    session_id: str | None = Depends(get_session_id),
    redis: Redis = Depends(get_redis),
) -> SessionData | None:
    if not session_id:
        return None
    raw = redis.get(session_key(session_id))
    if not raw:
        return None
    try:
        session = SessionData.model_validate_json(raw)
    except ValidationError:
        # Corrupt/incompatible payload (e.g. after a model change) — drop it
        # rather than 500ing, and treat it as if there's no active session.
        redis.delete(session_key(session_id))
        return None
    # Belt-and-suspenders alongside the Redis TTL; cleans up stale data on access
    if datetime.now(UTC) - session.created_at > timedelta(
        minutes=settings.SESSION_TIMEOUT_MINUTES
    ):
        redis.delete(session_key(session_id))
        return None
    return session
