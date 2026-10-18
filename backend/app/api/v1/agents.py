"""Agent runs API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.db import get_db
from app.core.security import require_role, verify_csrf
from app.models.worktree import Worktree, WorktreeStatus
from app.models.agent_run import AgentRun, AgentRunStatus
from app.schemas.agent_run import AgentRunRead, AgentRunCreate, AgentRunUpdate

router = APIRouter(prefix="/agent-runs", tags=["agent-runs"])


@router.get("", response_model=list[AgentRunRead])
async def list_agent_runs(
    skip: int = 0,
    limit: int = 100,
    worktree_id: Optional[str] = None,
    status: Optional[str] = None,
    agent_name: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(require_role("viewer")),
):
    """List agent runs with optional filtering."""
    query = db.query(AgentRun)
    if worktree_id:
        query = query.filter(AgentRun.worktree_id == worktree_id)
    if status:
        query = query.filter(AgentRun.status == status)
    if agent_name:
        query = query.filter(AgentRun.agent_name == agent_name)
    runs = query.order_by(AgentRun.created_at.desc()).offset(skip).limit(limit).all()
    return runs


@router.post("", response_model=AgentRunRead, status_code=status.HTTP_201_CREATED)
async def create_agent_run(
    run_in: AgentRunCreate,
    worktree_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role("operator")),
    csrf=Depends(verify_csrf),
):
    """Start a new agent run in a worktree."""
    worktree = db.get(Worktree, worktree_id)
    if not worktree:
        raise HTTPException(status_code=404, detail="Worktree not found")

    run = AgentRun(
        worktree_id=worktree.id,
        agent_name=run_in.agent_name,
        prompt=run_in.prompt,
        command=run_in.command or run_in.agent_name,
        status=AgentRunStatus.pending,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.get("/{run_id}", response_model=AgentRunRead)
async def get_agent_run(
    run_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role("viewer")),
):
    """Get an agent run by ID."""
    run = db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return run


@router.patch("/{run_id}", response_model=AgentRunRead)
async def update_agent_run(
    run_id: str,
    run_in: AgentRunUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_role("operator")),
    csrf=Depends(verify_csrf),
):
    """Update an agent run."""
    run = db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")

    update_data = run_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(run, field, value)

    run.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(run)
    return run


@router.post("/{run_id}/start", response_model=AgentRunRead)
async def start_agent_run(
    run_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role("operator")),
    csrf=Depends(verify_csrf),
):
    """Mark an agent run as started."""
    run = db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")

    if run.status != AgentRunStatus.pending:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start run with status {run.status}"
        )

    run.status = AgentRunStatus.running
    run.started_at = datetime.utcnow()
    db.commit()
    db.refresh(run)
    return run


@router.post("/{run_id}/stop", response_model=AgentRunRead)
async def stop_agent_run(
    run_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role("operator")),
    csrf=Depends(verify_csrf),
):
    """Stop a running agent run."""
    run = db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")

    if run.status not in (AgentRunStatus.running, AgentRunStatus.pending):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot stop run with status {run.status}"
        )

    run.status = AgentRunStatus.stopped
    run.finished_at = datetime.utcnow()
    db.commit()
    db.refresh(run)
    return run


@router.post("/{run_id}/complete", response_model=AgentRunRead)
async def complete_agent_run(
    run_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role("operator")),
    csrf=Depends(verify_csrf),
):
    """Mark an agent run as completed."""
    run = db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")

    if run.status != AgentRunStatus.running:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot complete run with status {run.status}"
        )

    run.status = AgentRunStatus.completed
    run.finished_at = datetime.utcnow()
    db.commit()
    db.refresh(run)
    return run


@router.get("/{run_id}/logs", response_model=dict)
async def get_agent_run_logs(
    run_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role("viewer")),
):
    """Get logs for an agent run."""
    run = db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")

    return {
        "run_id": run_id,
        "agent_name": run.agent_name,
        "status": run.status.value,
        "metrics": run.metrics or {},
        "created_at": run.created_at.isoformat(),
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }