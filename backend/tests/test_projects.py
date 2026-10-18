"""Tests for project management."""
import pytest
from app.models.project import Project, ProjectStatus
from app.schemas.project import ProjectCreate


class TestProjectModel:
    """Tests for the Project model."""

    def test_create_project_defaults(self, db_session):
        """Project defaults to pending status."""
        project = Project(
            name="test-project",
            git_url="https://github.com/example/repo.git",
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        assert project.id is not None
        assert len(project.id) == 26  # ULID length
        assert project.name == "test-project"
        assert project.status == ProjectStatus.pending
        assert project.base_ref == "main"
        assert project.created_at is not None
        assert project.updated_at is not None

    def test_project_requires_name(self, db_session):
        """Project name is required."""
        from sqlalchemy.exc import IntegrityError

        project = Project(name=None, git_url="https://github.com/example/repo.git")
        db_session.add(project)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_project_requires_git_url(self, db_session):
        """Project git_url is required."""
        from sqlalchemy.exc import IntegrityError

        project = Project(name="test", git_url=None)
        db_session.add(project)
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestProjectAPI:
    """Tests for the projects API endpoints."""

    def test_list_projects_empty(self, client, auth_headers):
        """List returns empty list when no projects exist."""
        resp = client.get("/api/v1/projects", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_and_retrieve_project(self, client, auth_headers, db_session):
        """Create a project and retrieve it."""
        resp = client.post(
            "/api/v1/projects",
            json={"name": "my-repo", "git_url": "https://github.com/example/repo.git"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "my-repo"
        assert data["git_url"] == "https://github.com/example/repo.git"
        assert data["status"] == "pending"

        # Retrieve the project
        project_id = data["id"]
        resp = client.get(f"/api/v1/projects/{project_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "my-repo"

    def test_create_project_unauthorized(self, client, monkeypatch):
        """Unauthorized users cannot create projects (when not in demo mode)."""
        monkeypatch.setenv("DEMO_MODE", "false")
        resp = client.post(
            "/api/v1/projects",
            json={"name": "test", "git_url": "https://github.com/test/repo.git"},
        )
        assert resp.status_code == 401

    def test_update_project(self, client, auth_headers):
        """Update project name and status."""
        resp = client.post(
            "/api/v1/projects",
            json={"name": "old-name", "git_url": "https://github.com/example/repo.git"},
            headers=auth_headers,
        )
        project_id = resp.json()["id"]

        resp = client.patch(
            f"/api/v1/projects/{project_id}",
            json={"name": "new-name", "status": "ready"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "new-name"
        assert data["status"] == "ready"

    def test_archive_project(self, client, auth_headers):
        """Archive a project (soft delete)."""
        resp = client.post(
            "/api/v1/projects",
            json={"name": "to-archive", "git_url": "https://github.com/example/repo.git"},
            headers=auth_headers,
        )
        project_id = resp.json()["id"]

        resp = client.delete(f"/api/v1/projects/{project_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "archived"

    def test_list_projects_filter_by_status(self, client, auth_headers):
        """Filter projects by status."""
        client.post(
            "/api/v1/projects",
            json={"name": "ready-proj", "git_url": "https://github.com/example/r1.git"},
            headers=auth_headers,
        )
        # Create another and set to ready
        resp = client.post(
            "/api/v1/projects",
            json={"name": "pending-proj", "git_url": "https://github.com/example/r2.git"},
            headers=auth_headers,
        )
        project_id = resp.json()["id"]
        client.patch(
            f"/api/v1/projects/{project_id}",
            json={"status": "ready"},
            headers=auth_headers,
        )

        resp = client.get("/api/v1/projects?status=ready", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "pending-proj"

    def test_list_projects_search(self, client, auth_headers):
        """Search projects by name."""
        client.post(
            "/api/v1/projects",
            json={"name": "alpha-project", "git_url": "https://github.com/example/alpha.git"},
            headers=auth_headers,
        )
        client.post(
            "/api/v1/projects",
            json={"name": "beta-project", "git_url": "https://github.com/example/beta.git"},
            headers=auth_headers,
        )

        resp = client.get("/api/v1/projects?search=alpha", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert "alpha" in data[0]["name"]

    def test_get_nonexistent_project(self, client, auth_headers):
        """404 for nonexistent project."""
        resp = client.get("/api/v1/projects/nonexistent", headers=auth_headers)
        assert resp.status_code == 404


class TestProjectClone:
    """Tests for the project clone/prepare endpoint."""

    def test_clone_ready_project_returns_current_state(self, client, auth_headers, db_session, git_repo):
        """Cloning an already ready project returns current state."""
        project = Project(
            name="ready-project",
            git_url=git_repo,
            status=ProjectStatus.ready,
            base_path=git_repo,
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        resp = client.post(
            f"/api/v1/projects/{project.id}/clone",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["base_path"] == git_repo

    def test_clone_archived_project_rejected(self, client, auth_headers, db_session):
        """Cannot clone an archived project."""
        project = Project(
            name="archived-project",
            git_url="https://github.com/example/repo.git",
            status=ProjectStatus.archived,
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        resp = client.post(
            f"/api/v1/projects/{project.id}/clone",
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "Cannot clone project with status" in resp.json()["detail"]

    def test_clone_nonexistent_project(self, client, auth_headers):
        """404 for nonexistent project."""
        resp = client.post(
            "/api/v1/projects/nonexistent/clone",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_clone_pending_project_with_real_repo(self, client, auth_headers, db_session, git_repo, monkeypatch):
        """Clone a pending project using a real local git repo."""
        # Override the git_worktree_base to a temp directory for the test
        import tempfile, os
        tmpdir = tempfile.mkdtemp(prefix="vectorhub-clone-test-")
        monkeypatch.setenv("GIT_WORKTREE_BASE", tmpdir)
        from app.core import security as sec_mod
        from app.services.git_service import GitService
        # Patch the global git_service in the projects module
        import app.api.v1.projects as projects_mod
        original_service = projects_mod.git_service
        test_service = GitService(base_path=tmpdir)
        projects_mod.git_service = test_service

        try:
            project = Project(
                name="test-clone-project",
                git_url=git_repo,
                status=ProjectStatus.pending,
            )
            db_session.add(project)
            db_session.commit()
            db_session.refresh(project)

            resp = client.post(
                f"/api/v1/projects/{project.id}/clone",
                headers=auth_headers,
            )
            assert resp.status_code == 200, f"Clone failed: {resp.text}"
            data = resp.json()
            assert data["status"] == "ready"
            assert data["base_path"] is not None
        finally:
            projects_mod.git_service = original_service
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)