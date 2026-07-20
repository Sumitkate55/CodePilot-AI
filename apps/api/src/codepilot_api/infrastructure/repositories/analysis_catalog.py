"""SQLAlchemy adapter for repository intelligence persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from codepilot_api.domain.repositories.entities import (
    RepositoryAnalysisPayload,
    RepositoryAnalysisRecord,
)
from codepilot_api.infrastructure.database.models.repository_analysis import RepositoryAnalysis


class SqlAlchemyRepositoryAnalysisStore:
    """Store the latest repeatable analysis for each immutable repository version."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_version(self, repository_version_id: UUID) -> RepositoryAnalysisRecord | None:
        model = await self._session.scalar(
            select(RepositoryAnalysis).where(
                RepositoryAnalysis.repository_version_id == repository_version_id
            )
        )
        return self._to_record(model) if model else None

    async def upsert(
        self, repository_version_id: UUID, payload: RepositoryAnalysisPayload
    ) -> RepositoryAnalysisRecord:
        model = await self._session.scalar(
            select(RepositoryAnalysis).where(
                RepositoryAnalysis.repository_version_id == repository_version_id
            )
        )
        if model is None:
            model = RepositoryAnalysis(
                repository_version_id=repository_version_id,
                analysis_version=payload.analysis_version,
                results=payload.results,
                file_count=payload.file_count,
                line_count=payload.line_count,
            )
            self._session.add(model)
        else:
            model.analysis_version = payload.analysis_version
            model.results = payload.results
            model.file_count = payload.file_count
            model.line_count = payload.line_count
            model.updated_at = datetime.now(UTC)
        await self._session.flush()
        return self._to_record(model)

    @staticmethod
    def _to_record(model: RepositoryAnalysis) -> RepositoryAnalysisRecord:
        return RepositoryAnalysisRecord(
            id=model.id,
            repository_version_id=model.repository_version_id,
            analysis_version=model.analysis_version,
            results=model.results,
            file_count=model.file_count,
            line_count=model.line_count,
            created_at=SqlAlchemyRepositoryAnalysisStore._as_utc(model.created_at),
            updated_at=SqlAlchemyRepositoryAnalysisStore._as_utc(model.updated_at),
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=UTC)
