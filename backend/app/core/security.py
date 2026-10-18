"""OIDC authentication with PKCE for SPA clients."""
import os
import secrets
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode

import httpx
from jose import jwt, JWTError
from fastapi import HTTPException, status, Depends, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings


@dataclass
class TokenData:
    """Parsed JWT token data."""
    sub: str
    email: Optional[str]
    name: Optional[str]
    roles: list[str]
    exp: int
    iat: int
    aud: str
    iss: str
    nonce: Optional[str] = None
    sid: Optional[str] = None


class OIDCClient:
    """OIDC client for authorization code flow with PKCE."""

    def __init__(self):
        self._jwks_cache: Optional[dict] = None
        self._jwks_fetched_at = 0
        self._jwks_ttl = 3600

    async def get_jwks(self) -> dict:
        """Fetch and cache JWKS from issuer."""
        if self._jwks_cache and (time.time() - self._jwks_fetched_at) < self._jwks_ttl:
            return self._jwks_cache

        jwks_uri = settings.oidc_jwks_uri or f"{settings.oidc_issuer}/protocol/openid-connect/certs"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(jwks_uri)
            resp.raise_for_status()
            self._jwks_cache = resp.json()
            self._jwks_fetched_at = time.time()
            return self._jwks_cache

    async def validate_token(self, token: str, expected_nonce: Optional[str] = None, audience: Optional[str] = None, access_token: Optional[str] = None) -> TokenData:
        """Validate access token or ID token."""
        try:
            jwks = await self.get_jwks()
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                audience=audience or settings.oidc_audience,
                access_token=access_token,
                issuer=settings.oidc_external_issuer or settings.oidc_issuer,
                options={"verify_aud": True, "verify_iss": True, "require_exp": True, "require_sub": True},
            )
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {e}",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify nonce if provided (for ID token validation)
        if expected_nonce and payload.get("nonce") != expected_nonce:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nonce mismatch",
            )

        roles = payload.get("realm_access", {}).get("roles", [])
        if "viewer" not in roles and "operator" not in roles and "admin" not in roles:
            roles = ["viewer"]  # default role

        return TokenData(
            sub=payload.get("sub", ""),
            email=payload.get("email"),
            name=payload.get("preferred_username") or payload.get("name"),
            roles=roles,
            exp=payload.get("exp", 0),
            iat=payload.get("iat", 0),
            aud=payload.get("aud", ""),
            iss=payload.get("iss", ""),
            nonce=payload.get("nonce"),
            sid=payload.get("sid"),
        )

    def build_auth_url(self, state: str, nonce: str, code_challenge: str) -> str:
        """Build OIDC authorization URL with PKCE using the browser-visible issuer."""
        issuer = settings.oidc_external_issuer or settings.oidc_issuer
        params = {
            "client_id": settings.oidc_client_id,
            "response_type": "code",
            "scope": "openid email profile roles",
            "redirect_uri": settings.oidc_redirect_uri,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{issuer}/protocol/openid-connect/auth?{urlencode(params)}"

    async def exchange_code(self, code: str, code_verifier: str) -> dict:
        """Exchange authorization code for tokens."""
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.oidc_client_id,
            "client_secret": settings.oidc_client_secret,
            "code": code,
            "redirect_uri": settings.oidc_redirect_uri,
            "code_verifier": code_verifier,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.oidc_issuer}/protocol/openid-connect/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Token exchange failed: {resp.text}",
                )
            return resp.json()

    async def logout_url(self, id_token_hint: Optional[str] = None) -> str:
        """Build logout URL."""
        params = {"client_id": settings.oidc_client_id}
        if id_token_hint:
            params["id_token_hint"] = id_token_hint
        params["post_logout_redirect_uri"] = "http://localhost:5173"
        return f"{settings.oidc_issuer}/protocol/openid-connect/logout?{urlencode(params)}"


oidc_client = OIDCClient()

# Session storage for PKCE verifiers (in-memory for demo; use Redis in prod)
_pkce_store: dict[str, tuple[str, float]] = {}  # state -> (code_verifier, expires_at)
_session_store: dict[str, dict] = {}  # session_id -> session_data


def generate_pkce_pair() -> tuple[str, str]:
    """Generate code_verifier and code_challenge (S256)."""
    code_verifier = secrets.token_urlsafe(32)
    import hashlib, base64
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip("=")
    return code_verifier, code_challenge


def store_pkce(state: str, code_verifier: str):
    """Store PKCE verifier with 10-minute TTL."""
    _pkce_store[state] = (code_verifier, time.time() + 600)


def consume_pkce(state: str) -> Optional[str]:
    """Consume and return PKCE verifier, or None if invalid/expired."""
    if state not in _pkce_store:
        return None
    verifier, expires = _pkce_store.pop(state)
    if time.time() > expires:
        return None
    return verifier


def create_session(data: dict) -> str:
    """Create session and return session ID."""
    session_id = secrets.token_urlsafe(32)
    _session_store[session_id] = {
        **data,
        "created_at": time.time(),
        "csrf_token": secrets.token_urlsafe(32),
    }
    return session_id


def get_session(session_id: str) -> Optional[dict]:
    """Get session by ID."""
    session = _session_store.get(session_id)
    if session and (time.time() - session["created_at"]) < 86400:  # 24h
        return session
    if session:
        _session_store.pop(session_id, None)
    return None


def delete_session(session_id: str):
    """Delete session."""
    _session_store.pop(session_id, None)


# FastAPI dependencies
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> TokenData:
    """Get current user from bearer token (SPA mode) or session cookie (cookie mode)."""
    if settings.is_demo_mode():
        # Demo mode: return fake user
        return TokenData(
            sub="demo-user",
            email="demo@vectorhub.local",
            name="Demo User",
            roles=["admin"],
            exp=int(time.time()) + 3600,
            iat=int(time.time()),
            aud=settings.oidc_audience,
            iss=settings.oidc_issuer,
        )

    # Try bearer token first (SPA mode)
    if credentials:
        return await oidc_client.validate_token(credentials.credentials)

    # Try session cookie (cookie mode)
    session_id = request.cookies.get(settings.session_cookie_name)
    if session_id:
        session = get_session(session_id)
        if session and "token_data" in session:
            if session["token_data"].get("exp", 0) <= time.time():
                delete_session(session_id)
                raise HTTPException(status_code=401, detail="Session token expired")
            return TokenData(**session["token_data"])

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(*allowed_roles: str):
    """Dependency factory for role-based access control."""
    async def _require_role(user: TokenData = Depends(get_current_user)) -> TokenData:
        if "admin" in user.roles:
            return user
        if not any(role in user.roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {allowed_roles}",
            )
        return user
    return _require_role


def set_auth_cookies(response: Response, session_id: str, csrf_token: str):
    """Set HttpOnly session cookie and CSRF cookie."""
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=86400,
        path="/",
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=86400,
        path="/",
    )


def clear_auth_cookies(response: Response):
    """Clear auth cookies."""
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")


async def verify_csrf(request: Request):
    """Verify CSRF token for cookie-authenticated writes."""
    if settings.is_demo_mode():
        return
    session_id = request.cookies.get(settings.session_cookie_name)
    if not session_id:
        raise HTTPException(status_code=403, detail="No session")
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=403, detail="Invalid session")
    csrf_header = request.headers.get("X-CSRF-Token")
    csrf_cookie = request.cookies.get(settings.csrf_cookie_name)
    expected = session.get("csrf_token", "")
    if not csrf_header or not csrf_cookie or not expected or not secrets.compare_digest(csrf_header, csrf_cookie) or not secrets.compare_digest(csrf_header, expected):
        raise HTTPException(status_code=403, detail="CSRF validation failed")