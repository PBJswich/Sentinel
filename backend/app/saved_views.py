"""
Saved views and filter presets storage.

Allows users to save filter and sort combinations for quick access.
"""

from typing import Dict, List, Optional
from datetime import date
from pydantic import BaseModel, Field

class SavedView(BaseModel):
    """Saved view with filter and sort configuration."""
    view_id: str = Field(..., description="Unique identifier for the view")
    name: str = Field(..., description="View name")
    description: Optional[str] = Field(None, description="Optional description")
    filters: Dict = Field(default_factory=dict, description="Filter parameters (market, category, direction, etc.)")
    sort_by: Optional[str] = Field(None, description="Sort option")
    created_at: date = Field(default_factory=date.today, description="Date view was created")
    updated_at: date = Field(default_factory=date.today, description="Date view was last updated")

# In-memory storage: maps view_id -> SavedView
_views: Dict[str, SavedView] = {}

def create_view(view: SavedView) -> SavedView:
    """Create a new saved view."""
    _views[view.view_id] = view
    return view

def get_view(view_id: str) -> Optional[SavedView]:
    """Get a saved view by ID."""
    return _views.get(view_id)

def get_all_views() -> List[SavedView]:
    """Get all saved views."""
    return list(_views.values())

def update_view(view_id: str, view: SavedView) -> Optional[SavedView]:
    """Update an existing saved view."""
    if view_id not in _views:
        return None
    view.updated_at = date.today()
    _views[view_id] = view
    return view

def delete_view(view_id: str) -> bool:
    """Delete a saved view."""
    if view_id in _views:
        del _views[view_id]
        return True
    return False

