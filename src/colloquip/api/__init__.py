"""Colloquip API — FastAPI application with REST + SSE + WebSocket."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from colloquip.api.app import SessionManager, create_session_manager
from colloquip.api.export_routes import router as export_router
from colloquip.api.external_routes import router as external_router
from colloquip.api.feedback_routes import router as feedback_router
from colloquip.api.memory_routes import router as memory_router
from colloquip.api.platform_routes import router as platform_router
from colloquip.api.routes import router
from colloquip.api.watcher_routes import router as watcher_router
from colloquip.api.ws import ws_router


def create_app(
    session_manager: SessionManager | None = None,
    database_url: str | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    db_url = database_url or os.environ.get("DATABASE_URL")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        if db_url:
            from colloquip.db.engine import create_engine_and_tables, get_async_session

            await create_engine_and_tables(db_url)
            app.state.session_manager._db_factory = get_async_session
        yield
        # Shutdown
        if db_url:
            from colloquip.db.engine import dispose_engine

            await dispose_engine()

    app = FastAPI(
        title="Colloquium",
        description="Emergent multi-agent deliberation API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS for web dashboard (credentials=False with wildcard origin per spec)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Session manager (injectable for testing)
    app.state.session_manager = session_manager or create_session_manager()

    # Routes
    app.include_router(router)
    app.include_router(platform_router)
    app.include_router(ws_router)
    app.include_router(memory_router)
    app.include_router(watcher_router)
    app.include_router(export_router)
    app.include_router(external_router)
    app.include_router(feedback_router)

    # Platform manager (auto-initialize on startup)
    from colloquip.api.platform_manager import PlatformManager

    app.state.platform_manager = PlatformManager()
    app.state.platform_manager.initialize()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    # Serve frontend static files (built by Vite into /app/static in Docker)
    static_dir = Path(__file__).resolve().parent.parent.parent.parent / "static"
    if static_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

        @app.get("/{path:path}")
        async def spa_catchall(path: str):
            # Serve actual files if they exist, otherwise fall back to index.html for SPA routing
            file = static_dir / path
            if path and file.is_file():
                return FileResponse(file)
            return FileResponse(static_dir / "index.html")

    return app
