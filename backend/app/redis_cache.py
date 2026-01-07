"""
Redis caching support (optional).

Provides Redis-based caching when Redis is available.
Falls back to in-memory cache if Redis is not configured.
"""

import os
import json
from typing import Optional, Any
from datetime import timedelta

_redis_client = None
_use_redis = False

def init_redis():
    """Initialize Redis connection if available."""
    global _redis_client, _use_redis
    
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return False
    
    try:
        import redis
        _redis_client = redis.from_url(redis_url, decode_responses=True)
        # Test connection
        _redis_client.ping()
        _use_redis = True
        return True
    except ImportError:
        print("Redis not installed. Install with: pip install redis")
        return False
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        return False

def get_cache(key: str) -> Optional[Any]:
    """Get value from cache."""
    if _use_redis and _redis_client:
        try:
            value = _redis_client.get(key)
            if value:
                return json.loads(value)
        except Exception:
            pass
    
    # Fallback to in-memory cache
    from .cache import get_cache as get_memory_cache
    return get_memory_cache(key)

def set_cache(key: str, value: Any, ttl_seconds: int = 3600):
    """Set value in cache with TTL."""
    if _use_redis and _redis_client:
        try:
            _redis_client.setex(key, ttl_seconds, json.dumps(value))
            return
        except Exception:
            pass
    
    # Fallback to in-memory cache
    from .cache import cache_result
    cache_result(key, value)

def delete_cache(key: str):
    """Delete value from cache."""
    if _use_redis and _redis_client:
        try:
            _redis_client.delete(key)
            return
        except Exception:
            pass
    
    # Fallback to in-memory cache
    from .cache import clear_cache
    # Note: clear_cache clears all, not just one key
    # For single key deletion in memory cache, would need to extend cache.py

