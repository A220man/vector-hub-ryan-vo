"""FastAPI application factory."""
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.config import settings
from app.core.db import init_db
from app.api.v1.projects import router as projects_router
from app.api.v1.worktrees import router as worktrees_router
from app.api.v1.agents import router as agents_router
from app.api.v1.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database on startup."""
    # Only init_db if not in test mode with in-memory DB that's managed per-test
    if hasattr(app, "root_path") and app.root_path == "/test":
        pass  # Tests manage their own DB
    else:
        init_db()
    yield


def create_app(test_mode: bool = False) -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        description="Vector Hub - AI agent orchestration platform",
        version=os.getenv("VERSION", "1.0.0"),
        root_path="/test" if test_mode else "",
        lifespan=lifespan,
    )

    # CORS - allow frontend origin
    if settings.debug:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://localhost:5173",
                "http://localhost:3000",
                "https://vector-hub.example.com",
            ],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["*"],
        )

    # Health check
    @app.get("/health")
    async def health():
        return {"status": "ok", "version": app.version}

    # Version endpoint
    @app.get("/version")
    async def version():
        return {"version": app.version, "name": settings.app_name}

    # Include routers
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(worktrees_router, prefix="/api/v1")
    app.include_router(agents_router, prefix="/api/v1")

    # Exception handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        import logging
        logging.getLogger(__name__).exception(f"Unhandled error: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    return app


# Create the app instance
app = create_app()
