"""Projects API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pathlib import Path
from datetime import datetime
from tempfile import TemporaryDirectory

from app.core.db import get_db
from app.core.security import require_role, verify_csrf
from app.models.project import Project, ProjectStatus
from app.schemas.project import ProjectRead, ProjectCreate, ProjectUpdate
from app.services.git_service import GitService

router = APIRouter(prefix="/projects", tags=["projects"])

git_service = GitService()


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(require_role("viewer")),
):
    """List projects with optional filtering."""
    query = db.query(Project)
    if status:
        query = query.filter(Project.status == status)
    if search:
        query = query.filter(
            (Project.name.ilike(f"%{search}%")) |
            (Project.git_url.ilike(f"%{search}%"))
        )
    projects = query.offset(skip).limit(limit).all()
    return projects


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role("operator")),
    csrf=Depends(verify_csrf),
):
    """Create a new project."""
    project = Project(
        name=project_in.name,
        git_url=project_in.git_url,
        base_ref=project_in.base_ref,
        status=ProjectStatus.pending,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/clone", response_model=ProjectRead)
def clone_project(
    project_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role("operator")),
    csrf=Depends(verify_csrf),
):
    """Clone the project repository and mark it ready for worktree operations."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status == ProjectStatus.ready and project.base_path:
        return project

    if project.status == ProjectStatus.archived:
        raise HTTPException(status_code=400, detail=f"Cannot clone project with status: {project.status}")

    # Claim the operation atomically so competing requests cannot clone twice.
    claimed = db.query(Project).filter(
        Project.id == project_id,
        Project.status.in_([ProjectStatus.pending, ProjectStatus.error]),
    ).update({Project.status: ProjectStatus.cloning, Project.error_message: None},
             synchronize_session=False)
    db.commit()
    if not claimed:
        raise HTTPException(status_code=409, detail="Project cannot be cloned in its current state")
    db.refresh(project)

    target_path = Path(git_service.base_path) / project.id
    try:
        # Isolate partial clones; failed attempts must not poison the retry path.
        with TemporaryDirectory(prefix=".clone-", dir=git_service.base_path) as staging:
            staged_repo = Path(staging) / "repository"
            result = git_service.clone_project(project.git_url, staged_repo, project.base_ref)
            if not result.success:
                raise RuntimeError(result.error or "Git clone failed")
            if target_path.exists():
                raise RuntimeError("Project destination already exists; recovery is required")
            staged_repo.rename(target_path)
        project.base_path = str(target_path)
        project.status = ProjectStatus.ready
        project.error_message = None
    except Exception as exc:
        project.status = ProjectStatus.error
        project.error_message = str(exc)[:2000] or "Git clone failed"
        project.base_path = None

    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role("viewer")),
):
    """Get a project by ID."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: str,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_role("operator")),
    csrf=Depends(verify_csrf),
):
    """Update a project."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status == ProjectStatus.cloning:
        raise HTTPException(status_code=409, detail="Project clone is in progress")

    update_data = project_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", response_model=ProjectRead)
async def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
    csrf=Depends(verify_csrf),
):
    """Archive a project (soft delete)."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for worktree in project.worktrees:
        worktree.status = "archived"

    if project.status == ProjectStatus.cloning:
        raise HTTPException(status_code=409, detail="Project clone is in progress")

    project.status = ProjectStatus.archived
    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)
    return project