"""Application configuration."""
import os
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Core
    app_name: str = "Vector Hub"
    debug: bool = False
    environment: str = "development"
    
    # Database
    database_url: str = Field(
        default="sqlite:///./vectorhub.db",
        env="DATABASE_URL"
    )
    
    # Auth / OIDC
    # oidc_issuer is the internal URL used for token exchange and JWKS fetch.
    # oidc_external_issuer is the public issuer used for authorization URLs and JWT iss validation.
    # When not set, oidc_external_issuer falls back to oidc_issuer (same-host deployments).
    oidc_issuer: str = Field(default="http://localhost:8080/realms/vectorhub", env="OIDC_ISSUER")
    oidc_external_issuer: str = Field(default="", env="OIDC_EXTERNAL_ISSUER")
    oidc_client_id: str = Field(default="vector-hub", env="OIDC_CLIENT_ID")
    oidc_client_secret: str = Field(default="", env="OIDC_CLIENT_SECRET")
    oidc_redirect_uri: str = Field(default="http://localhost:5173/auth/callback", env="OIDC_REDIRECT_URI")
    oidc_audience: str = Field(default="vector-hub-api", env="OIDC_AUDIENCE")
    oidc_jwks_uri: Optional[str] = Field(default=None, env="OIDC_JWKS_URI")
    
    # Demo mode (local only)
    demo_mode: bool = Field(default=False, env="DEMO_MODE")
    
    # LLM (server-side only, opt-in)
    llm_api_key: Optional[str] = Field(default=None, env="LLM_API_KEY")
    llm_provider: str = Field(default="openai", env="LLM_PROVIDER")
    llm_model: str = Field(default="gpt-3.5-turbo", env="LLM_MODEL")
    llm_base_url: Optional[str] = Field(default=None, env="LLM_BASE_URL")
    llm_timeout_seconds: int = Field(default=30, env="LLM_TIMEOUT_SECONDS")
    
    # Git
    git_worktree_base: str = Field(default="/tmp/vectorhub-worktrees")
    
    # Host binding
    host: str = "127.0.0.1"
    port: int = 8000
    
    # Session
    secret_key: str = Field(default="change-me-in-production", env="SECRET_KEY")
    session_cookie_name: str = "vectorhub_session"
    
    # CSRF
    csrf_cookie_name: str = "vectorhub_csrf"

    class Config:
        env_file = ".env"
        case_sensitive = False

    def is_demo_mode(self) -> bool:
        """Check demo mode, re-reading env to support test overrides."""
        return os.environ.get("DEMO_MODE", "").lower() in ("true", "1", "yes")


settings = Settings()
