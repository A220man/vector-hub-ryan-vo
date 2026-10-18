"""Project model."""
import enum
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Enum
from sqlalchemy.orm import relationship
from ulid import ULID
import ulid as ulid_mod

from app.core.db import Base


class ProjectStatus(str, enum.Enum):
    """Project lifecycle status."""
    pending = "pending"
    cloning = "cloning"
    ready = "ready"
    error = "error"
    archived = "archived"


def generate_ulid() -> str:
    """Generate a ULID string."""
    return str(ulid_mod.new())


class Project(Base):
    """A git project managed by Vector Hub."""
    __tablename__ = "projects"

    id: str = Column(String(26), primary_key=True, default=generate_ulid)
    name: str = Column(String(255), nullable=False, index=True)
    git_url: str = Column(Text, nullable=False)
    base_ref: str = Column(String(255), nullable=False, default="main")
    base_path: str = Column(Text, nullable=True)
    status: ProjectStatus = Column(Enum(ProjectStatus), nullable=False, default=ProjectStatus.pending)
    error_message: str = Column(Text, nullable=True)

    created_at: datetime = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    worktrees = relationship("Worktree", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name}, status={self.status})>"
