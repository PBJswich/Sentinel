"""
Rate limiting middleware.

Simple in-memory rate limiting. For production, use Redis-based rate limiting.
"""

import time
from typing import Dict, Tuple
from collections import defaultdict
from fastapi import Request, HTTPException, status

# Rate limit storage: {api_key: [(timestamp, count), ...]}
_rate_limits: Dict[str, list] = defaultdict(list)

def check_rate_limit(api_key: str, limit: int = 100, window_seconds: int = 60) -> Tuple[bool, int]:
    """
    Check if request is within rate limit.
    
    Args:
        api_key: API key or identifier
        limit: Maximum requests per window
        window_seconds: Time window in seconds
        
    Returns:
        Tuple of (is_allowed, remaining_requests)
    """
    current_time = time.time()
    cutoff_time = current_time - window_seconds
    
    # Clean old entries
    requests = _rate_limits[api_key]
    requests[:] = [ts for ts in requests if ts > cutoff_time]
    
    # Check limit
    if len(requests) >= limit:
        return False, 0
    
    # Add current request
    requests.append(current_time)
    remaining = limit - len(requests)
    
    return True, remaining

async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware."""
    # Get API key from header
    api_key = request.headers.get("X-API-Key", "anonymous")
    
    # Get rate limit from API key info or use default
    limit = 100  # Default: 100 requests per minute
    if api_key != "anonymous":
        from .auth import get_api_key_info
        key_info = get_api_key_info(api_key)
        if key_info:
            limit = key_info.get("rate_limit", 100)
    
    # Check rate limit
    allowed, remaining = check_rate_limit(api_key, limit=limit)
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Limit: {limit} requests per minute.",
            headers={"X-RateLimit-Limit": str(limit), "X-RateLimit-Remaining": "0"}
        )
    
    # Add rate limit headers
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    
    return response

