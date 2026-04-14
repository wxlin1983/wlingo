from __future__ import annotations

import redis
from redis import Redis
from .config import settings

redis_client: Redis[str] = redis.from_url(settings.REDIS_URL, decode_responses=True)
