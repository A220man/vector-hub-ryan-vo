"""Tests for worktree and agent run API."""
import pytest
from app.models.project import Project, ProjectStatus
from app.models.worktree import Worktree, WorktreeStatus
from app.models.agent_run import AgentRun, AgentRunStatus
from app.schemas.worktree import WorktreeCreate
from app.schemas.agent_run import AgentRunCreate


class TestWorktreeAPI:
    """Tests for worktree API."""

    def _create_project(self, db_session, base_path="/tmp/test-repo"):
        """Helper to create a ready project."""
        project = Project(
            name="test-project",
            git_url="https://github.com/example/repo.git",
            status=ProjectStatus.ready,
            base_path=base_path,
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)
        return project

    def test_list_worktrees_empty(self, client, auth_headers, db_session):
        """Empty worktree list."""
        resp = client.get("/api/v1/worktrees", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_worktree_requires_ready_project(self, client, auth_headers, db_session):
        """Cannot create worktree on a non-ready project."""
        project = Project(
            name="pending-project",
            git_url="https://github.com/example/repo.git",
            status=ProjectStatus.pending,
            base_path="/tmp/test-repo",
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        resp = client.post(
            f"/api/v1/worktrees/{project.id}",
            json={"name": "wt1", "branch": "feature/test", "start_ref": "main"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "not ready" in resp.json()["detail"]

    def test_create_worktree_for_project(self, client, auth_headers, db_session, git_repo):
        """Create a worktree and it appears in list."""
        project = self._create_project(db_session, base_path=git_repo)

        resp = client.post(
            f"/api/v1/worktrees/{project.id}",
            json={"name": "test-worktree", "branch": "feature/test", "start_ref": "main"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "test-worktree"
        assert data["branch"] == "feature/test"
        assert data["project_id"] == project.id
        assert data["status"] == "ready"

        # List should contain it
        resp = client.get("/api/v1/worktrees", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_worktree(self, client, auth_headers, db_session):
        """Get a worktree by ID."""
        project = self._create_project(db_session)
        worktree = Worktree(
            project_id=project.id,
            name="test-wt",
            branch="feature/test",
            start_ref="main",
            status=WorktreeStatus.ready,
        )
        db_session.add(worktree)
        db_session.commit()
        db_session.refresh(worktree)

        resp = client.get(f"/api/v1/worktrees/{worktree.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "test-wt"

    def test_filter_worktrees_by_project(self, client, auth_headers, db_session):
        """Filter worktrees by project_id."""
        project1 = self._create_project(db_session)
        project2 = Project(
            name="project2",
            git_url="https://github.com/example/repo2.git",
            status=ProjectStatus.ready,
            base_path="/tmp/test-repo2",
        )
        db_session.add(project2)
        db_session.commit()
        db_session.refresh(project2)

        for i, proj_id in enumerate([project1.id, project2.id]):
            wt = Worktree(
                project_id=proj_id,
                name=f"wt-{i}",
                branch="main",
                start_ref="main",
                status=WorktreeStatus.ready,
            )
            db_session.add(wt)
        db_session.commit()

        resp = client.get(f"/api/v1/worktrees?project_id={project1.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

    def test_full_workflow_create_clone_worktree(self, client, auth_headers, db_session, git_repo, monkeypatch):
        """Full workflow: create project, clone it, then create a worktree."""
        import tempfile, shutil
        import app.api.v1.projects as projects_mod
        from app.services.git_service import GitService

        tmpdir = tempfile.mkdtemp(prefix="vectorhub-workflow-test-")
        original_service = projects_mod.git_service
        projects_mod.git_service = GitService(base_path=tmpdir)

        try:
            # 1. Create a project
            resp = client.post(
                "/api/v1/projects",
                json={"name": "workflow-test", "git_url": git_repo},
                headers=auth_headers,
            )
            assert resp.status_code == 201
            project_id = resp.json()["id"]
            assert resp.json()["status"] == "pending"

            # 2. Clone the project (prepare it)
            resp = client.post(
                f"/api/v1/projects/{project_id}/clone",
                headers=auth_headers,
            )
            assert resp.status_code == 200, f"Clone failed: {resp.text}"
            project = resp.json()
            assert project["status"] == "ready"
            assert project["base_path"] is not None

            # 3. Create a worktree from the cloned project
            resp = client.post(
                f"/api/v1/worktrees/{project_id}",
            json={"name": "feature-branch", "branch": "feature/test", "start_ref": "main"},
                headers=auth_headers,
            )
            assert resp.status_code == 201, f"Worktree creation failed: {resp.text}"
            worktree = resp.json()
            assert worktree["name"] == "feature-branch"
            assert worktree["status"] == "ready"

            # 4. The worktree should appear in the list
            resp = client.get("/api/v1/worktrees", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["name"] == "feature-branch"
        finally:
            projects_mod.git_service = original_service
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestAgentRunAPI:
    """Tests for agent run API."""

    def test_create_and_start_agent_run(self, client, auth_headers, db_session):
        """Create an agent run and transition it through lifecycle."""
        project = Project(
            name="test-project",
            git_url="https://github.com/example/repo.git",
            status=ProjectStatus.ready,
            base_path="/tmp/test-repo",
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        worktree = Worktree(
            project_id=project.id,
            name="test-wt",
            branch="feature/test",
            start_ref="main",
            status=WorktreeStatus.ready,
        )
        db_session.add(worktree)
        db_session.commit()
        db_session.refresh(worktree)

        # Create agent run
        resp = client.post(
            f"/api/v1/agent-runs?worktree_id={worktree.id}",
            json={"agent_name": "claude-code", "prompt": "Fix the bug in main.py"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        run_id = resp.json()["id"]
        assert resp.json()["status"] == "pending"

        # Start it
        resp = client.post(f"/api/v1/agent-runs/{run_id}/start", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"
        assert resp.json()["started_at"] is not None

        # Complete it
        resp = client.post(f"/api/v1/agent-runs/{run_id}/complete", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"
        assert resp.json()["finished_at"] is not None

    def test_stop_running_agent(self, client, auth_headers, db_session):
        """Stop a running agent run."""
        project = Project(name="p", git_url="url", status=ProjectStatus.ready, base_path="/tmp/r")
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        worktree = Worktree(project_id=project.id, name="wt", branch="main", start_ref="main", status=WorktreeStatus.ready)
        db_session.add(worktree)
        db_session.commit()
        db_session.refresh(worktree)

        resp = client.post(
            f"/api/v1/agent-runs?worktree_id={worktree.id}",
            json={"agent_name": "codex", "prompt": "test"},
            headers=auth_headers,
        )
        run_id = resp.json()["id"]

        resp = client.post(f"/api/v1/agent-runs/{run_id}/start", headers=auth_headers)
        resp = client.post(f"/api/v1/agent-runs/{run_id}/stop", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "stopped"

    def test_start_non_pending_run_fails(self, client, auth_headers, db_session):
        """Cannot start a non-pending run."""
        project = Project(name="p", git_url="url", status=ProjectStatus.ready, base_path="/tmp/r")
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        worktree = Worktree(project_id=project.id, name="wt", branch="main", start_ref="main", status=WorktreeStatus.ready)
        db_session.add(worktree)
        db_session.commit()
        db_session.refresh(worktree)

        resp = client.post(
            f"/api/v1/agent-runs?worktree_id={worktree.id}",
            json={"agent_name": "codex"},
            headers=auth_headers,
        )
        run_id = resp.json()["id"]

        # Start and complete
        client.post(f"/api/v1/agent-runs/{run_id}/start", headers=auth_headers)
        client.post(f"/api/v1/agent-runs/{run_id}/complete", headers=auth_headers)

        # Try to start again (should fail - already completed)
        resp = client.post(f"/api/v1/agent-runs/{run_id}/start", headers=auth_headers)
        assert resp.status_code == 400

    def test_list_agent_runs_filter(self, client, auth_headers, db_session):
        """List agent runs filtered by agent name."""
        project = Project(name="p", git_url="url", status=ProjectStatus.ready, base_path="/tmp/r")
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        worktree = Worktree(project_id=project.id, name="wt", branch="main", start_ref="main", status=WorktreeStatus.ready)
        db_session.add(worktree)
        db_session.commit()
        db_session.refresh(worktree)

        for agent in ["claude-code", "codex", "opencode"]:
            run = AgentRun(worktree_id=worktree.id, agent_name=agent, status=AgentRunStatus.pending)
            db_session.add(run)
        db_session.commit()

        resp = client.get("/api/v1/agent-runs?agent_name=claude-code", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["agent_name"] == "claude-code"
