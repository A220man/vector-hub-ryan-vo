"""API v1 package."""
from app.api.v1.projects import router as projects_router
from app.api.v1.worktrees import router as worktrees_router
from app.api.v1.agents import router as agents_router
from app.api.v1.auth import router as auth_router

__all__ = [
    "projects_router",
    "worktrees_router",
    "agents_router",
    "auth_router",
]