"""Shared fixtures for API tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

import codepilot_api.infrastructure.database.models  # noqa: F401
from codepilot_api.config.settings import AiProvider, AppEnvironment, Settings
from codepilot_api.infrastructure.database.base import Base
from codepilot_api.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Return isolated settings that do not require PostgreSQL."""
    return Settings(
        app_env=AppEnvironment.TESTING,
        database_url="sqlite+aiosqlite://",
        repository_storage_root=tmp_path / "repository-storage",
        trusted_hosts=["testserver"],
        cors_origins=["http://localhost:5173"],
        ai_provider=AiProvider.OPENAI,
        openai_api_key=None,
    )


@pytest.fixture
async def app(settings: Settings):
    """Return an isolated application with all relational models created."""
    app = create_app(settings)
    async with app.state.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield app
    async with app.state.engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await app.state.engine.dispose()


@pytest.fixture
async def client(app) -> AsyncClient:
    """Return a test HTTP client backed by the isolated application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
