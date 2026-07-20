"""Repository source intelligence use cases."""

from __future__ import annotations

import asyncio
from uuid import UUID

from codepilot_api.application.repositories.contracts import (
    RepositoryAnalysisStore,
    RepositoryAnalyzer,
    RepositoryCatalog,
    RepositoryStorage,
)
from codepilot_api.domain.repositories.entities import RepositoryAnalysisRecord, RepositoryRecord
from codepilot_api.domain.repositories.errors import (
    RepositoryAnalysisError,
    RepositoryAnalysisNotFound,
    RepositoryNotFound,
)


class RepositoryIntelligenceService:
    """Analyze the newest source version and retain a bounded, repeatable profile."""

    def __init__(
        self,
        repository_catalog: RepositoryCatalog,
        analysis_store: RepositoryAnalysisStore,
        storage: RepositoryStorage,
        analyzer: RepositoryAnalyzer,
    ) -> None:
        self._repository_catalog = repository_catalog
        self._analysis_store = analysis_store
        self._storage = storage
        self._analyzer = analyzer

    async def analyze_latest(self, owner_id: UUID, repository_id: UUID) -> RepositoryAnalysisRecord:
        """Run an analysis against the latest immutable source version for a repository."""
        repository = await self._get_repository(owner_id, repository_id)
        if not repository.versions:
            raise RepositoryAnalysisError("The repository has no stored source version to analyze.")
        version = repository.versions[0]
        source_root = self._storage.resolve_storage_key(version.storage_key)
        payload = await asyncio.to_thread(self._analyzer.analyze, source_root)
        return await self._analysis_store.upsert(version.id, payload)

    async def get_latest(self, owner_id: UUID, repository_id: UUID) -> RepositoryAnalysisRecord:
        """Return the saved profile for the newest source version, if it exists."""
        repository = await self._get_repository(owner_id, repository_id)
        if not repository.versions:
            raise RepositoryAnalysisNotFound
        version = repository.versions[0]
        analysis = await self._analysis_store.get_by_version(version.id)
        if analysis is None:
            raise RepositoryAnalysisNotFound
        return analysis

    async def _get_repository(self, owner_id: UUID, repository_id: UUID) -> RepositoryRecord:
        repository = await self._repository_catalog.get_by_owner(owner_id, repository_id)
        if repository is None:
            raise RepositoryNotFound
        return repository
