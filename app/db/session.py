"""
Async database engine, session factory, and FastAPI dependency.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.db.base import Base

_engine_kwargs: dict[str, Any] = {}


def _build_engine_kwargs() -> dict[str, Any]:
    """Return engine kwargs, adjusting for SQLite vs PostgreSQL."""
    settings = get_settings()
    url = settings.DATABASE_URL
    kwargs: dict[str, Any] = {
        "echo": settings.DEBUG,
    }
    if url.startswith("sqlite"):
        # aiosqlite requires check_same_thread=False
        kwargs["connect_args"] = {"check_same_thread": False}
        # SQLite doesn't support pool_size / max_overflow
        kwargs["pool_pre_ping"] = False
    else:
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20
        kwargs["pool_pre_ping"] = True
    return kwargs


engine = create_async_engine(
    get_settings().DATABASE_URL,
    **_build_engine_kwargs(),
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    The session is committed on success, rolled back on exception,
    and closed in all cases.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables.  **Dev / testing fallback only** – use Alembic in production."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
