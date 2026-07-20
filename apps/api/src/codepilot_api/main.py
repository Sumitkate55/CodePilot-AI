"""FastAPI application factory and runtime entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from codepilot_api.application.health.service import ReadinessService
from codepilot_api.config.settings import Settings, get_settings
from codepilot_api.infrastructure.database.session import create_engine, create_session_factory
from codepilot_api.infrastructure.logging.configuration import configure_logging
from codepilot_api.presentation.api.v1.router import api_router
from codepilot_api.presentation.errors import register_exception_handlers
from codepilot_api.presentation.middleware.request_context import RequestContextMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create a fully configured API application for a selected environment."""
    active_settings = settings or get_settings()
    configure_logging(active_settings)
    engine = create_engine(active_settings)
    session_factory = create_session_factory(engine)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        yield
        await application.state.engine.dispose()

    app = FastAPI(
        title=active_settings.app_name,
        version=active_settings.app_version,
        description="CodePilot AI backend API.",
        docs_url="/docs" if not active_settings.is_production else None,
        redoc_url=None,
        openapi_url=f"{active_settings.api_v1_prefix}/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = active_settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.readiness_service = ReadinessService(session_factory)

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=active_settings.trusted_hosts)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )
    register_exception_handlers(app, active_settings)
    app.include_router(api_router, prefix=active_settings.api_v1_prefix)
    return app


app = create_app()
