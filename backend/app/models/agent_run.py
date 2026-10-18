"""AgentRun model."""
import enum
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Enum, ForeignKey, JSON, Integer
from sqlalchemy.orm import relationship

from app.core.db import Base
from app.models.project import generate_ulid


class AgentRunStatus(str, enum.Enum):
    """Agent run lifecycle status."""
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    stopped = "stopped"


class AgentRun(Base):
    """A coding agent run within a worktree."""
    __tablename__ = "agent_runs"

    id: str = Column(String(26), primary_key=True, default=generate_ulid)
    worktree_id: str = Column(String(26), ForeignKey("worktrees.id", ondelete="CASCADE"), nullable=False)
    agent_name: str = Column(String(100), nullable=False)  # e.g. "claude-code", "codex", "opencode"
    command: str = Column(Text, nullable=True)  # full command including args
    prompt: str = Column(Text, nullable=True)
    status: AgentRunStatus = Column(Enum(AgentRunStatus), nullable=False, default=AgentRunStatus.pending)
    started_at: datetime = Column(DateTime(timezone=True), nullable=True)
    finished_at: datetime = Column(DateTime(timezone=True), nullable=True)

    # Usage tracking
    input_tokens: int = Column(Integer, nullable=True)
    output_tokens: int = Column(Integer, nullable=True)
    cost_cents: int = Column(Integer, nullable=True)

    created_at: datetime = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    worktree = relationship("Worktree", back_populates="agent_runs")

    def __repr__(self):
        return f"<AgentRun(id={self.id}, agent={self.agent_name}, status={self.status})>"
