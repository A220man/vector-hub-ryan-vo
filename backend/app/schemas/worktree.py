"""Worktree schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.worktree import WorktreeStatus


class WorktreeBase(BaseModel):
    """Base worktree schema."""
    name: str = Field(..., min_length=1, max_length=255)
    branch: str = Field(..., min_length=1, max_length=255)
    start_ref: str = Field(default="main")


class WorktreeCreate(WorktreeBase):
    """Create worktree request."""
    pass


class WorktreeUpdate(BaseModel):
    """Update worktree request."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    branch: Optional[str] = Field(default=None)
    status: Optional[WorktreeStatus] = None
    error_message: Optional[str] = None


class WorktreeRead(WorktreeBase):
    """Worktree read schema."""
    id: str
    project_id: str
    path: Optional[str] = None
    status: WorktreeStatus
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
