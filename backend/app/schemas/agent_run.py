"""AgentRun schemas."""
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field

from app.models.agent_run import AgentRunStatus


class AgentRunBase(BaseModel):
    """Base agent run schema."""
    agent_name: str = Field(..., min_length=1, max_length=100)
    prompt: Optional[str] = Field(default=None)
    command: Optional[str] = Field(default=None)


class AgentRunCreate(AgentRunBase):
    """Create agent run request."""
    pass


class AgentRunUpdate(BaseModel):
    """Update agent run request."""
    status: Optional[AgentRunStatus] = None
    prompt: Optional[str] = None
    command: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost_cents: Optional[int] = None
    metrics: Optional[dict[str, Any]] = None


class AgentRunRead(AgentRunBase):
    """Agent run read schema."""
    id: str
    worktree_id: str
    status: AgentRunStatus
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost_cents: Optional[int] = None
    metrics: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
