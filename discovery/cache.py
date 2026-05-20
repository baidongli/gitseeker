import hashlib
import json
import logging
from functools import wraps

from django.core.cache import cache

logger = logging.getLogger(__name__)


def _make_key(prefix, args, kwargs):
    raw = json.dumps([args, sorted(kwargs.items())], default=str, sort_keys=True)
    return f"{prefix}:{hashlib.md5(raw.encode()).hexdigest()[:16]}"


def cached(prefix, ttl=600):
    """Cache a function's return value.

    Skips caching when the result is None or carries an `error` key (API failures),
    so transient failures don't get pinned in the cache.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = _make_key(prefix, args, kwargs)
            value = cache.get(key)
            if value is not None:
                return value
            result = func(*args, **kwargs)
            if result is None:
                return result
            if isinstance(result, dict) and result.get("error"):
                return result
            try:
                cache.set(key, result, ttl)
            except Exception as e:
                logger.warning("Cache set failed for %s: %s", key, e)
            return result
        return wrapper
    return decorator


def clear_all():
    cache.clear()
