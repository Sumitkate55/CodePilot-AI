"""SQLAlchemy adapter for AI project-summary persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from codepilot_api.domain.summaries.entities import ProjectSummaryPayload, ProjectSummaryRecord
from codepilot_api.infrastructure.database.models.repository_summary import RepositorySummary


class SqlAlchemyProjectSummaryStore:
    """Store the current structured summary for each immutable source version."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_version(self, repository_version_id: UUID) -> ProjectSummaryRecord | None:
        model = await self._session.scalar(
            select(RepositorySummary).where(
                RepositorySummary.repository_version_id == repository_version_id
            )
        )
        return self._to_record(model) if model else None

    async def upsert(
        self, repository_version_id: UUID, payload: ProjectSummaryPayload
    ) -> ProjectSummaryRecord:
        model = await self._session.scalar(
            select(RepositorySummary).where(
                RepositorySummary.repository_version_id == repository_version_id
            )
        )
        if model is None:
            model = RepositorySummary(
                repository_version_id=repository_version_id,
                model=payload.model,
                prompt_version=payload.prompt_version,
                content=payload.content,
            )
            self._session.add(model)
        else:
            model.model = payload.model
            model.prompt_version = payload.prompt_version
            model.content = payload.content
            model.updated_at = datetime.now(UTC)
        await self._session.flush()
        return self._to_record(model)

    @staticmethod
    def _to_record(model: RepositorySummary) -> ProjectSummaryRecord:
        return ProjectSummaryRecord(
            id=model.id,
            repository_version_id=model.repository_version_id,
            model=model.model,
            prompt_version=model.prompt_version,
            content=model.content,
            created_at=SqlAlchemyProjectSummaryStore._as_utc(model.created_at),
            updated_at=SqlAlchemyProjectSummaryStore._as_utc(model.updated_at),
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=UTC)
