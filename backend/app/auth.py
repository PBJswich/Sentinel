"""
Authentication and authorization.

Simple API key-based authentication for MVP. Can be extended with OAuth/JWT later.
"""

import os
import secrets
from typing import Optional
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

# API Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# In-memory API key storage (in production, use database)
# Format: {api_key: {"user_id": str, "permissions": list, "rate_limit": int}}
_api_keys: dict[str, dict] = {}

def generate_api_key() -> str:
    """Generate a new API key."""
    return secrets.token_urlsafe(32)

def register_api_key(user_id: str, permissions: list[str] = None, rate_limit: int = 100) -> str:
    """
    Register a new API key.
    
    Args:
        user_id: User identifier
        permissions: List of permissions (e.g., ["read", "write"])
        rate_limit: Requests per minute
        
    Returns:
        Generated API key
    """
    api_key = generate_api_key()
    _api_keys[api_key] = {
        "user_id": user_id,
        "permissions": permissions or ["read"],
        "rate_limit": rate_limit
    }
    return api_key

def get_api_key_info(api_key: str) -> Optional[dict]:
    """Get information about an API key."""
    return _api_keys.get(api_key)

def revoke_api_key(api_key: str) -> bool:
    """Revoke an API key."""
    if api_key in _api_keys:
        del _api_keys[api_key]
        return True
    return False

def require_api_key(
    api_key: Optional[str] = Security(api_key_header),
    required_permission: Optional[str] = None
) -> dict:
    """
    Dependency to require API key authentication.
    
    Args:
        api_key: API key from header
        required_permission: Optional permission required (e.g., "write")
        
    Returns:
        API key info dict
        
    Raises:
        HTTPException if authentication fails
    """
    # Check if authentication is enabled
    auth_enabled = os.getenv("ENABLE_AUTH", "false").lower() == "true"
    
    if not auth_enabled:
        # Authentication disabled - allow all requests
        return {"user_id": "anonymous", "permissions": ["read", "write"], "rate_limit": 1000}
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header."
        )
    
    key_info = get_api_key_info(api_key)
    if not key_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Check permission if required
    if required_permission and required_permission not in key_info.get("permissions", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{required_permission}' required"
        )
    
    return key_info

