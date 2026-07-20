"""Health use cases."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from codepilot_api.domain.health.entities import DependencyHealth, HealthStatus, ReadinessReport


class ReadinessService:
    """Checks dependencies needed to safely receive application traffic."""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory

    async def check(self) -> ReadinessReport:
        """Check database connectivity without modifying application data."""
        try:
            async with self._session_factory() as session:
                await session.execute(text("SELECT 1"))
        except Exception:
            database = DependencyHealth(name="database", status=HealthStatus.UNAVAILABLE)
            return ReadinessReport(status=HealthStatus.UNAVAILABLE, dependencies=(database,))

        database = DependencyHealth(name="database", status=HealthStatus.HEALTHY)
        return ReadinessReport(status=HealthStatus.HEALTHY, dependencies=(database,))
