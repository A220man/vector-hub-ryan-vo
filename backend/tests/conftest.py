"""Test configuration and fixtures."""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test env vars before importing app
os.environ["DEMO_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OIDC_CLIENT_SECRET"] = "test-secret"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing"

from app.core.db import Base, get_db
from app.main import create_app


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def git_repo_path(test_engine):
    """Create a real git repo for integration tests."""
    tmpdir = tempfile.mkdtemp(prefix="vectorhub-test-")
    repo_path = Path(tmpdir) / "test-repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=str(repo_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(repo_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(repo_path), capture_output=True)

    # Create initial commit
    (repo_path / "README.md").write_text("# Test Repo\n")
    subprocess.run(["git", "add", "."], cwd=str(repo_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(repo_path), capture_output=True)
    subprocess.run(["git", "branch", "-m", "main"], cwd=str(repo_path), capture_output=True)

    yield str(repo_path)
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def db_session(test_engine):
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        # Clean up all data
        db.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(text(f"DELETE FROM {table.name}"))
        db.commit()
        # Clean up worktree filesystem
        import shutil
        from pathlib import Path
        wt_base = Path("/tmp/vectorhub-worktrees")
        if wt_base.exists():
            for wt_dir in wt_base.iterdir():
                if wt_dir.is_dir():
                    shutil.rmtree(wt_dir, ignore_errors=True)
        db.close()


@pytest.fixture
def client(db_session):
    """Create test client with overridden DB dependency."""
    def override_get_db():
        yield db_session

    app = create_app(test_mode=True)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client):
    """Get auth headers for demo mode."""
    resp = client.post("/api/v1/auth/demo-login", json={"email": "test@test.com", "name": "Test User"})
    assert resp.status_code == 200, f"Demo login failed: {resp.text}"
    session_cookie = resp.cookies.get("vectorhub_session")
    csrf_cookie = resp.cookies.get("vectorhub_csrf")
    return {
        "Cookie": f"vectorhub_session={session_cookie}; vectorhub_csrf={csrf_cookie}",
        "X-CSRF-Token": csrf_cookie,
    }


@pytest.fixture
def git_repo(git_repo_path):
    """Provide git repo path."""
    return git_repo_path
