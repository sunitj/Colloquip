"""Database engine and session factory."""

import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from colloquip.db.tables import Base

# Default to SQLite for development
_DEFAULT_URL = "sqlite+aiosqlite:///colloquip.db"


def _get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", _DEFAULT_URL)
    # Convert postgres:// to postgresql+asyncpg:// if needed
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


_engine = None
_session_factory = None


async def create_engine_and_tables(database_url: str | None = None):
    """Create the async engine and initialize all tables.

    Call this once at application startup.
    """
    global _engine, _session_factory

    url = database_url or _get_database_url()
    _engine = create_async_engine(url, echo=False)
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine():
    """Dispose of the engine. Call at shutdown."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None


def get_async_session() -> AsyncSession:
    """Get a new async database session."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call create_engine_and_tables() first.")
    return _session_factory()
