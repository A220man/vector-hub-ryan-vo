"""Worktree model."""
import enum
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.db import Base
from app.models.project import generate_ulid


class WorktreeStatus(str, enum.Enum):
    """Worktree lifecycle status."""
    creating = "creating"
    ready = "ready"
    error = "error"
    archived = "archived"


class Worktree(Base):
    """A git worktree managed by Vector Hub."""
    __tablename__ = "worktrees"

    id: str = Column(String(26), primary_key=True, default=generate_ulid)
    project_id: str = Column(String(26), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: str = Column(String(255), nullable=False)
    branch: str = Column(String(255), nullable=False)
    start_ref: str = Column(String(255), nullable=False, default="main")
    path: str = Column(Text, nullable=True)
    status: WorktreeStatus = Column(Enum(WorktreeStatus), nullable=False, default=WorktreeStatus.creating)
    error_message: str = Column(Text, nullable=True)

    created_at: datetime = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="worktrees")
    agent_runs = relationship("AgentRun", back_populates="worktree", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Worktree(id={self.id}, name={self.name}, branch={self.branch})>"
