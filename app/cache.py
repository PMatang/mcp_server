from cachetools import TTLCache, cached
from app.config import settings
import asyncio

# Simple in-memory TTL cache. Swap this for Redis in production.
_global_cache = TTLCache(maxsize=settings.MAX_CACHE_SIZE, ttl=settings.CACHE_TTL_SECONDS)

def get_cache():
    return _global_cache

def cached_result(key):
    """Decorator factory for caching async/sync call results keyed by `key` string."""
    def decorator(fn):
        async def wrapper(*args, **kwargs):
            cache = get_cache()
            if key in cache:
                return cache[key]
            result = await fn(*args, **kwargs) if asyncio.iscoroutinefunction(fn) else fn(*args, **kwargs)
            cache[key] = result
            return result
        return wrapper
    return decorator
