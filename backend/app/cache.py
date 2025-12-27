"""
In-memory caching layer.

Provides caching for frequently accessed data to improve performance.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import json

# Simple in-memory cache
_cache: Dict[str, Dict[str, Any]] = {}

def _make_cache_key(*args, **kwargs) -> str:
    """Generate a cache key from function arguments."""
    key_data = {
        "args": args,
        "kwargs": sorted(kwargs.items())
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()

def cache_result(ttl_seconds: int = 300):
    """
    Decorator to cache function results.
    
    Args:
        ttl_seconds: Time to live in seconds (default: 5 minutes)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{_make_cache_key(*args, **kwargs)}"
            
            # Check cache
            if cache_key in _cache:
                cached_data = _cache[cache_key]
                if datetime.now() - cached_data["timestamp"] < timedelta(seconds=ttl_seconds):
                    return cached_data["value"]
            
            # Call function and cache result
            result = func(*args, **kwargs)
            _cache[cache_key] = {
                "value": result,
                "timestamp": datetime.now()
            }
            
            return result
        
        return wrapper
    return decorator

def clear_cache(pattern: Optional[str] = None):
    """
    Clear cache entries.
    
    Args:
        pattern: Optional pattern to match cache keys (if None, clears all)
    """
    if pattern is None:
        _cache.clear()
    else:
        keys_to_remove = [k for k in _cache.keys() if pattern in k]
        for key in keys_to_remove:
            del _cache[key]

def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    total_entries = len(_cache)
    total_size = sum(len(str(v)) for v in _cache.values())
    
    return {
        "total_entries": total_entries,
        "total_size_bytes": total_size,
        "cache_keys": list(_cache.keys())[:10]  # First 10 keys
    }

