"""Ports required by AI project-summary use cases."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from codepilot_api.domain.summaries.entities import (
    ProjectSummaryContext,
    ProjectSummaryPayload,
    ProjectSummaryRecord,
)


class ProjectSummaryAgent(Protocol):
    """Generate a structured project summary from bounded repository evidence."""

    async def generate(self, context: ProjectSummaryContext) -> ProjectSummaryPayload: ...


class ProjectSummaryStore(Protocol):
    """Persist and retrieve one current summary for each repository version."""

    async def get_by_version(self, repository_version_id: UUID) -> ProjectSummaryRecord | None: ...

    async def upsert(
        self, repository_version_id: UUID, payload: ProjectSummaryPayload
    ) -> ProjectSummaryRecord: ...
