"""Project schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.project import ProjectStatus


class ProjectBase(BaseModel):
    """Base project schema."""
    name: str = Field(..., min_length=1, max_length=255)
    git_url: str = Field(..., min_length=1)
    base_ref: str = Field(default="main")


class ProjectCreate(ProjectBase):
    """Create project request."""
    name: str = Field(..., min_length=1, max_length=255)
    git_url: str = Field(..., min_length=1)


class ProjectCreateResponse(BaseModel):
    """Response for project creation with optional clone results."""
    project: "ProjectRead"


class ProjectUpdate(BaseModel):
    """Update project request."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    git_url: Optional[str] = Field(default=None)
    base_ref: Optional[str] = Field(default=None)
    status: Optional[ProjectStatus] = None
    error_message: Optional[str] = None


class ProjectRead(ProjectBase):
    """Project read schema."""
    id: str
    status: ProjectStatus
    error_message: Optional[str] = None
    base_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
