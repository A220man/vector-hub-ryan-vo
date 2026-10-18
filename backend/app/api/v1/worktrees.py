"""Worktrees API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime
from typing import Optional

from app.core.db import get_db
from app.core.security import require_role, verify_csrf
from app.models.project import Project, ProjectStatus
from app.models.worktree import Worktree, WorktreeStatus
from app.schemas.worktree import WorktreeRead, WorktreeCreate, WorktreeUpdate
from app.services.git_service import GitService
from app.config import settings as app_config

router = APIRouter(prefix="/worktrees", tags=["worktrees"])

git_service = GitService()


@router.get("", response_model=list[WorktreeRead])
async def list_worktrees(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(require_role("viewer")),
):
    """List worktrees with optional filtering."""
    query = db.query(Worktree)
    if status:
        query = query.filter(Worktree.status == status)
    if project_id:
        query = query.filter(Worktree.project_id == project_id)
    if search:
        query = query.filter(
            (Worktree.name.ilike(f"%{search}%")) |
            (Worktree.branch.ilike(f"%{search}%"))
        )
    worktrees = query.offset(skip).limit(limit).all()
    return worktrees


@router.post("/{project_id}", response_model=WorktreeRead, status_code=status.HTTP_201_CREATED)
async def create_worktree_for_project(
    project_id: str,
    worktree_in: WorktreeCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role("operator")),
    csrf=Depends(verify_csrf),
):
    """Create a new worktree from a project."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status != ProjectStatus.ready:
        raise HTTPException(
            status_code=400,
            detail=f"Project is not ready (status: {project.status})"
        )

    worktree = Worktree(
        project_id=project.id,
        name=worktree_in.name,
        branch=worktree_in.branch,
        start_ref=worktree_in.start_ref,
        status=WorktreeStatus.creating,
    )
    db.add(worktree)
    db.commit()
    db.refresh(worktree)

    # Execute git worktree creation
    if project.base_path:
        repo_path = Path(project.base_path)
    else:
        raise HTTPException(
            status_code=400,
            detail="Project has no base path. Project must be cloned first."
        )

    result = git_service.create_worktree(
        repo_path=repo_path,
        branch=worktree_in.branch,
        start_ref=worktree_in.start_ref,
        worktree_name=worktree_in.name
    )

    if result.success:
        worktree.status = WorktreeStatus.ready
        worktree.path = str(git_service.base_path / worktree_in.name)
    else:
        worktree.status = WorktreeStatus.error
        worktree.error_message = result.error

    worktree.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(worktree)
    return worktree


@router.get("/{worktree_id}", response_model=WorktreeRead)
async def get_worktree(
    worktree_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role("viewer")),
):
    """Get a worktree by ID."""
    worktree = db.get(Worktree, worktree_id)
    if not worktree:
        raise HTTPException(status_code=404, detail="Worktree not found")
    return worktree


@router.delete("/{worktree_id}", response_model=WorktreeRead)
async def delete_worktree(
    worktree_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
    csrf=Depends(verify_csrf),
):
    """Remove a worktree (archives it)."""
    worktree = db.get(Worktree, worktree_id)
    if not worktree:
        raise HTTPException(status_code=404, detail="Worktree not found")

    if worktree.path and worktree.project and worktree.project.base_path:
        result = git_service.remove_worktree(
            repo_path=Path(worktree.project.base_path),
            worktree_path=Path(worktree.path)
        )
        if not result.success:
            worktree.error_message = result.error

    worktree.status = WorktreeStatus.archived
    worktree.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(worktree)
    return worktree


@router.get("/{worktree_id}/diff", response_model=dict)
async def get_worktree_diff(
    worktree_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role("viewer")),
):
    """Get diff for a worktree against its start ref."""
    worktree = db.get(Worktree, worktree_id)
    if not worktree:
        raise HTTPException(status_code=404, detail="Worktree not found")

    if not worktree.path:
        raise HTTPException(status_code=400, detail="Worktree has no path")

    import subprocess
    try:
        proc = subprocess.run(
            ["git", "diff", "--stat"],
            capture_output=True, text=True, timeout=30,
            cwd=str(worktree.path)
        )
        diff_stat = proc.stdout if proc.returncode == 0 else proc.stderr
    except Exception as e:
        diff_stat = f"Error: {e}"

    proc = subprocess.run(
        ["git", "diff"],
        capture_output=True, text=True, timeout=30,
        cwd=str(worktree.path)
    )

    return {
        "worktree_id": worktree_id,
        "diff_stat": diff_stat,
        "diff": proc.stdout,
        "start_ref": worktree.start_ref,
    }