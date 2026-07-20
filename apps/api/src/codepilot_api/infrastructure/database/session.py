"""Async SQLAlchemy engine and session factory construction."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from codepilot_api.config.settings import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    """Create the process-level asynchronous SQLAlchemy engine."""
    options: dict[str, object] = {"pool_pre_ping": True}
    if settings.database_url.startswith("sqlite+"):
        options["connect_args"] = {"check_same_thread": False}
    else:
        options["pool_size"] = 10
        options["max_overflow"] = 20
        options["pool_recycle"] = 1800

    return create_async_engine(settings.database_url, echo=settings.debug, **options)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Build sessions that never autocommit and expire no objects after a response."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)


async def get_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped session and guarantee it closes after the request."""
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
