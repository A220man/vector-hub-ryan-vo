"""Auth API routes."""
from fastapi import APIRouter, Request, Response, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.security import (
    oidc_client, generate_pkce_pair, store_pkce, consume_pkce,
    create_session, get_session, delete_session, set_auth_cookies, clear_auth_cookies,
    verify_csrf, require_role, get_current_user
)
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Login initiation request."""
    pass


class LoginResponse(BaseModel):
    """Login initiation response."""
    auth_url: str
    state: str


class CallbackRequest(BaseModel):
    """OAuth callback request."""
    code: str
    state: str


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


class UserResponse(BaseModel):
    """Current user response."""
    sub: str
    email: str | None
    name: str | None
    roles: list[str]


class DemoLoginRequest(BaseModel):
    """Demo login request (for local development only)."""
    email: str = "demo@vectorhub.local"
    name: str = "Demo User"


@router.get("/login", response_model=LoginResponse)
async def login(request: Request, response: Response):
    """Bind a one-use PKCE transaction to the initiating browser."""
    import secrets
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier, challenge = generate_pkce_pair()
    store_pkce(state, verifier)
    transaction = create_session({"nonce": nonce, "state": state})
    response.set_cookie(settings.session_cookie_name + "_login", transaction,
                        httponly=True, secure=settings.cookie_secure,
                        samesite="lax", max_age=600, path="/")
    return LoginResponse(auth_url=oidc_client.build_auth_url(state, nonce, challenge), state=state)


@router.get("/callback")
async def callback(code: str, state: str, request: Request):
    """Validate the browser transaction and tokens, then return session cookies."""
    import secrets
    import time
    from fastapi.responses import RedirectResponse
    cookie = settings.session_cookie_name + "_login"
    transaction_id = request.cookies.get(cookie, "")
    transaction = get_session(transaction_id)
    if (not transaction or time.time() - transaction["created_at"] >= 600
            or not secrets.compare_digest(transaction.get("state", ""), state)):
        raise HTTPException(status_code=400, detail="Invalid or expired login transaction")
    verifier = consume_pkce(state)
    delete_session(transaction_id)
    if not verifier:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    tokens = await oidc_client.exchange_code(code, verifier)
    if not tokens.get("access_token") or not tokens.get("id_token"):
        raise HTTPException(status_code=400, detail="Required tokens missing")
    identity = await oidc_client.validate_token(tokens["id_token"],
        expected_nonce=transaction["nonce"], audience=settings.oidc_client_id,
        access_token=tokens["access_token"])
    token_data = await oidc_client.validate_token(tokens["access_token"])
    if not identity.sub or identity.sub != token_data.sub:
        raise HTTPException(status_code=401, detail="Token subject mismatch")
    from dataclasses import asdict
    session_id = create_session({"token_data": asdict(token_data),
        "access_token": tokens["access_token"], "id_token": tokens["id_token"]})
    response = RedirectResponse("/", status_code=303)
    set_auth_cookies(response, session_id, get_session(session_id)["csrf_token"])
    response.delete_cookie(cookie, path="/")
    return response


@router.post("/demo-login")
async def demo_login(request: DemoLoginRequest, response: Response):
    """Demo login for local development (only works in demo mode)."""
    if not settings.is_demo_mode():
        raise HTTPException(status_code=403, detail="Demo mode not enabled")
    
    session_id = create_session({
        "token_data": {
            "sub": "demo-user",
            "email": request.email,
            "name": request.name,
            "roles": ["admin"],
            "exp": int(__import__('time').time()) + 3600,
            "iat": int(__import__('time').time()),
            "aud": settings.oidc_audience,
            "iss": settings.oidc_issuer,
        }
    })
    set_auth_cookies(response, session_id, get_session(session_id)["csrf_token"])
    return {"message": "Logged in as demo user"}


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Logout and clear session."""
    session_id = request.cookies.get(settings.session_cookie_name)
    if session_id:
        delete_session(session_id)
    clear_auth_cookies(response)
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def me(user=Depends(get_current_user)):
    """Get current user info."""
    return UserResponse(
        sub=user.sub,
        email=user.email,
        name=user.name,
        roles=user.roles,
    )


@router.get("/csrf")
async def get_csrf(request: Request):
    """Get CSRF token for cookie-authenticated writes."""
    session_id = request.cookies.get(settings.session_cookie_name)
    if not session_id:
        raise HTTPException(status_code=403, detail="No session")
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=403, detail="Invalid session")
    return {"csrf_token": session.get("csrf_token", "")}