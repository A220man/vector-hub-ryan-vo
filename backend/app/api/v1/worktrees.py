"""Worktrees API routes."""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user=Depends(require_role("operator")),
    csrf=Depends(verify_csrf),
):
    """Create a new worktree from a project (async background task)."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status != ProjectStatus.ready:
        raise HTTPException(
            status_code=400,
            detail=f"Project is not ready (status: {project.status})"
        )

    if not project.base_path:
        raise HTTPException(
            status_code=400,
            detail="Project has no base path. Project must be cloned first."
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

    # Check if we're in test mode (in-memory DB)
    is_test_mode = db.bind.url.database == ":memory:" or "/test" in str(db.bind.url)

    # Schedule git worktree creation as background task
    background_tasks.add_task(
        _create_worktree_background,
        worktree_id=worktree.id,
        repo_path=project.base_path,
        branch=worktree_in.branch,
        start_ref=worktree_in.start_ref,
        worktree_name=worktree_in.name,
        is_test_mode=is_test_mode,
    )

    return worktree


async def _create_worktree_background(
    worktree_id: str,
    repo_path: str,
    branch: str,
    start_ref: str,
    worktree_name: str,
    is_test_mode: bool = False,
):
    """Background task to create git worktree."""
    from app.core.db import SessionLocal
    from app.models.worktree import Worktree, WorktreeStatus
    from app.services.git_service import GitService
    
    db = SessionLocal()
    git_service = GitService()
    try:
        worktree = db.get(Worktree, worktree_id)
        if not worktree:
            return
        
        if is_test_mode:
            # Run synchronously in tests
            result = git_service.create_worktree(
                repo_path=Path(repo_path),
                branch=branch,
                start_ref=start_ref,
                worktree_name=worktree_name
            )
        else:
            result = await git_service.create_worktree_async(
                repo_path=Path(repo_path),
                branch=branch,
                start_ref=start_ref,
                worktree_name=worktree_name
            )
        
        if result.success:
            worktree.status = WorktreeStatus.ready
            worktree.path = str(git_service.base_path / worktree_name)
        else:
            worktree.status = WorktreeStatus.error
            worktree.error_message = result.error
        
        from datetime import datetime, timezone
        worktree.updated_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as e:
        worktree = db.get(Worktree, worktree_id)
        if worktree:
            worktree.status = WorktreeStatus.error
            worktree.error_message = str(e)
            from datetime import datetime, timezone
            worktree.updated_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
    csrf=Depends(verify_csrf),
):
    """Remove a worktree (archives it)."""
    worktree = db.get(Worktree, worktree_id)
    if not worktree:
        raise HTTPException(status_code=404, detail="Worktree not found")

    # Check if we're in test mode (in-memory DB)
    is_test_mode = db.bind.url.database == ":memory:" or "/test" in str(db.bind.url)

    if worktree.path and worktree.project and worktree.project.base_path:
        # Schedule git worktree removal as background task
        background_tasks.add_task(
            _remove_worktree_background,
            worktree_id=worktree.id,
            repo_path=worktree.project.base_path,
            worktree_path=worktree.path,
            is_test_mode=is_test_mode,
        )

    worktree.status = WorktreeStatus.archived
    from datetime import datetime, timezone
    worktree.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(worktree)
    return worktree


async def _remove_worktree_background(
    worktree_id: str,
    repo_path: str,
    worktree_path: str,
    is_test_mode: bool = False,
):
    """Background task to remove git worktree."""
    from app.core.db import SessionLocal
    from app.models.worktree import Worktree, WorktreeStatus
    from app.services.git_service import GitService
    
    db = SessionLocal()
    git_service = GitService()
    try:
        worktree = db.get(Worktree, worktree_id)
        if not worktree:
            return
        
        if is_test_mode:
            # Run synchronously in tests
            result = git_service.remove_worktree(
                repo_path=Path(repo_path),
                worktree_path=Path(worktree_path)
            )
        else:
            result = await git_service.remove_worktree_async(
                repo_path=Path(repo_path),
                worktree_path=Path(worktree_path)
            )
        
        if not result.success:
            worktree.error_message = result.error
        
        from datetime import datetime, timezone
        worktree.updated_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as e:
        worktree = db.get(Worktree, worktree_id)
        if worktree:
            worktree.error_message = str(e)
            from datetime import datetime, timezone
            worktree.updated_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


@router.post("/{project_id}/sync", response_model=list[WorktreeRead])
async def sync_worktrees(
    project_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user=Depends(require_role("operator")),
    csrf=Depends(verify_csrf),
):
    """Sync worktrees with actual git worktrees for a project."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not project.base_path:
        raise HTTPException(status_code=400, detail="Project has no base path")
    
    # List actual git worktrees
    git_worktrees = git_service.list_worktrees(Path(project.base_path))
    
    # Create/update worktree records
    for gw in git_worktrees:
        # Skip the main worktree (the repo itself)
        if gw.get("path") == project.base_path:
            continue
        
        worktree_name = Path(gw.get("path", "")).name
        branch = gw.get("branch", "")
        
        # Check if worktree exists in DB
        existing = db.query(Worktree).filter(
            Worktree.project_id == project.id,
            Worktree.name == worktree_name
        ).first()
        
        if existing:
            existing.path = gw["path"]
            existing.branch = branch
            existing.status = WorktreeStatus.ready
            from datetime import datetime, timezone
            existing.updated_at = datetime.now(timezone.utc)
        else:
            new_wt = Worktree(
                project_id=project.id,
                name=worktree_name,
                branch=branch,
                path=gw["path"],
                status=WorktreeStatus.ready,
            )
            db.add(new_wt)
    
    db.commit()
    
    # Return updated list
    worktrees = db.query(Worktree).filter(Worktree.project_id == project.id).all()
    return worktrees

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