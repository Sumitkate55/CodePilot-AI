"""Framework-independent health status entities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class HealthStatus(StrEnum):
    """A service or dependency health state."""

    HEALTHY = "healthy"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class DependencyHealth:
    """Health result for one dependency."""

    name: str
    status: HealthStatus


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    """Aggregate dependency status for the readiness endpoint."""

    status: HealthStatus
    dependencies: tuple[DependencyHealth, ...]
