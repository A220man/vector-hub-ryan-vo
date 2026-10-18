"""Tests for authentication and security."""
import pytest
from app.core.security import generate_pkce_pair, store_pkce, consume_pkce, create_session, get_session, delete_session
from app.models.project import ProjectStatus


class TestAuthAPI:
    """Tests for auth API endpoints."""

    def test_login_initiates_pkce(self, client):
        """Login endpoint returns auth URL and state."""
        resp = client.get("/api/v1/auth/login")
        assert resp.status_code == 200
        data = resp.json()
        assert "auth_url" in data
        assert "state" in data

    def test_me_returns_user_in_demo(self, client):
        """Demo mode returns user info."""
        # Login in demo mode
        resp = client.post("/api/v1/auth/demo-login", json={})
        assert resp.status_code == 200

        # Use session cookie
        session_cookie = resp.cookies.get("vectorhub_session")
        csrf_cookie = resp.cookies.get("vectorhub_csrf")

        headers = {
            "Cookie": f"vectorhub_session={session_cookie}; vectorhub_csrf={csrf_cookie}",
            "X-CSRF-Token": csrf_cookie,
        }
        resp = client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 200
        user = resp.json()
        assert user["email"] == "demo@vectorhub.local"
        assert "admin" in user["roles"]

    def test_unauthenticated_access_rejected(self, client, monkeypatch):
        """Unauthenticated requests are rejected (when not in demo mode)."""
        monkeypatch.setenv("DEMO_MODE", "false")
        resp = client.get("/api/v1/projects")
        assert resp.status_code == 401

    def test_logout_clears_session(self, client):
        """Logout clears the session cookie."""
        resp = client.post("/api/v1/auth/demo-login", json={})
        session_cookie = resp.cookies.get("vectorhub_session")

        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 200

        # Check cookie is cleared
        assert resp.cookies.get("vectorhub_session") is None or \
               resp.cookies.get("vectorhub_session") == ""


class TestPKCE:
    """Tests for PKCE utilities."""

    def test_generate_pkce_pair(self):
        """PKCE pair generation produces valid verifier and challenge."""
        verifier, challenge = generate_pkce_pair()
        assert len(verifier) >= 43
        assert len(challenge) >= 43
        assert verifier != challenge

    def test_store_and_consume_pkce(self):
        """PKCE can be stored and consumed once."""
        state = "test-state-123"
        verifier = "test-verifier"
        store_pkce(state, verifier)

        retrieved = consume_pkce(state)
        assert retrieved == verifier

        # Second consume returns None (one-time use)
        retrieved2 = consume_pkce(state)
        assert retrieved2 is None

    def test_consume_invalid_pkce(self):
        """Consuming unknown state returns None."""
        result = consume_pkce("nonexistent-state")
        assert result is None

    def test_expired_pkce(self):
        """Expired PKCE state is rejected."""
        store_pkce("expired-state", "verifier")
        # Simulate expiry by manually expiring
        from app.core.security import _pkce_store
        import time
        _pkce_store["expired-state"] = ("verifier", time.time() - 1)

        result = consume_pkce("expired-state")
        assert result is None


class TestSession:
    """Tests for session management."""

    def test_create_and_get_session(self):
        """Session can be created and retrieved."""
        session_id = create_session({"user": "test"})
        assert session_id is not None
        session = get_session(session_id)
        assert session is not None
        assert session["user"] == "test"
        assert "csrf_token" in session

    def test_get_invalid_session(self):
        """Invalid session returns None."""
        result = get_session("nonexistent-session")
        assert result is None

    def test_delete_session(self):
        """Session deletion works."""
        session_id = create_session({"user": "test"})
        delete_session(session_id)
        assert get_session(session_id) is None