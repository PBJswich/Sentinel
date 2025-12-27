"""
In-memory watchlist storage.

Stores user watchlists for signals and markets.
"""

from typing import Dict, List, Optional
from datetime import date
from .models import Watchlist

# In-memory storage: maps watchlist_id -> Watchlist
_watchlists: Dict[str, Watchlist] = {}

def create_watchlist(watchlist: Watchlist) -> Watchlist:
    """Create a new watchlist."""
    _watchlists[watchlist.watchlist_id] = watchlist
    return watchlist

def get_watchlist(watchlist_id: str) -> Optional[Watchlist]:
    """Get a watchlist by ID."""
    return _watchlists.get(watchlist_id)

def get_all_watchlists() -> List[Watchlist]:
    """Get all watchlists."""
    return list(_watchlists.values())

def update_watchlist(watchlist_id: str, watchlist: Watchlist) -> Optional[Watchlist]:
    """Update an existing watchlist."""
    if watchlist_id not in _watchlists:
        return None
    watchlist.updated_at = date.today()
    _watchlists[watchlist_id] = watchlist
    return watchlist

def delete_watchlist(watchlist_id: str) -> bool:
    """Delete a watchlist."""
    if watchlist_id in _watchlists:
        del _watchlists[watchlist_id]
        return True
    return False

