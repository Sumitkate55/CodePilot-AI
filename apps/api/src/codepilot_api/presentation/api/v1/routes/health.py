"""Liveness and readiness endpoints."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from codepilot_api.domain.health.entities import HealthStatus

router = APIRouter()


class ServiceHealthResponse(BaseModel):
    """Liveness response payload."""

    model_config = ConfigDict(frozen=True)

    status: Literal["healthy"] = "healthy"
    service: str
    version: str


class DependencyResponse(BaseModel):
    """One readiness dependency response."""

    model_config = ConfigDict(frozen=True)

    name: str
    status: HealthStatus


class ReadinessResponse(BaseModel):
    """Readiness response payload."""

    model_config = ConfigDict(frozen=True)

    status: HealthStatus
    dependencies: list[DependencyResponse]


@router.get("/health", response_model=ServiceHealthResponse, include_in_schema=False)
async def health(request: Request) -> ServiceHealthResponse:
    """Return process liveness without contacting external dependencies."""
    settings = request.app.state.settings
    return ServiceHealthResponse(service=settings.app_name, version=settings.app_version)


@router.get("/ready", response_model=ReadinessResponse, include_in_schema=False)
async def readiness(request: Request) -> ReadinessResponse | JSONResponse:
    """Return readiness only when the database connection can be used."""
    report = await request.app.state.readiness_service.check()
    response = ReadinessResponse(
        status=report.status,
        dependencies=[
            DependencyResponse(name=item.name, status=item.status) for item in report.dependencies
        ],
    )
    if report.status == HealthStatus.HEALTHY:
        return response
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=response.model_dump(),
    )
