"""
Utility routines.
"""

import celery
import redis


def get_redis_con(app: celery.Celery) -> redis.Redis:
    """
    Get the underlying Redis connection, assuming that the Celery application is
    connected to Redis.
    """
    # mypy doesn't know what `app.backend` is, but Pygin is guaranteed to always
    # use the Redis backend for this.
    return app.backend.client  # type: ignore[attr-defined]
