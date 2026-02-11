"""Colloquip API — FastAPI application with REST + SSE + WebSocket."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from colloquip.api.app import SessionManager, create_session_manager
from colloquip.api.routes import router
from colloquip.api.ws import ws_router


def create_app(session_manager: SessionManager | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Colloquip",
        description="Emergent multi-agent deliberation API",
        version="0.1.0",
    )

    # CORS for web dashboard
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Session manager (injectable for testing)
    app.state.session_manager = session_manager or create_session_manager()

    # Routes
    app.include_router(router)
    app.include_router(ws_router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
