"""
Redis-backed fixed-window rate limiter. Applied only to routes that either
cost money to call (LLM calls via /api/chat) or trigger financial actions
(/api/payments/simulate, approve/reject) — read-only routes (list mandates,
history) aren't limited here.

Fixed-window is a deliberate simplicity choice for a prototype: it's not
perfectly smooth (a burst right at a window boundary can technically allow
close to 2x the limit), but it needs no extra library beyond the redis
client we already depend on, and that imprecision doesn't matter at this
scale. A sliding-window or token-bucket algorithm would be the production
upgrade.
"""

import uuid

import redis
from fastapi import Depends

from app.api.deps import get_current_user_id
from app.core.config import get_settings
from app.core.exceptions import RateLimitExceededError

_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(get_settings().redis_url)
    return _redis_client


def rate_limit(key_prefix: str, max_requests: int, window_seconds: int):
    """
    Returns a FastAPI dependency enforcing `max_requests` per `window_seconds`
    per (key_prefix, user_id) pair. Use as:
        Depends(rate_limit("chat", max_requests=20, window_seconds=60))
    """

    def _dependency(user_id: uuid.UUID = Depends(get_current_user_id)) -> None:
        r = _get_redis()
        key = f"ratelimit:{key_prefix}:{user_id}"
        count = r.incr(key)
        if count == 1:
            r.expire(key, window_seconds)
        if count > max_requests:
            raise RateLimitExceededError(
                f"Too many requests to '{key_prefix}' — limit is {max_requests} per {window_seconds}s.",
                detail={"retry_after_seconds": r.ttl(key)},
            )

    return _dependency