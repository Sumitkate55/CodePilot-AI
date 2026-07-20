"""Repository-wide code-review use cases."""

from __future__ import annotations

import asyncio
from uuid import UUID

from codepilot_api.application.repositories.contracts import (
    RepositoryAnalysisStore,
    RepositoryCatalog,
    RepositoryStorage,
)
from codepilot_api.application.reviews.contracts import (
    RepositoryCodeReviewer,
    RepositoryCodeReviewStore,
)
from codepilot_api.domain.repositories.errors import (
    RepositoryAnalysisNotFound,
    RepositoryNotFound,
)
from codepilot_api.domain.reviews.entities import RepositoryCodeReviewRecord
from codepilot_api.domain.reviews.errors import RepositoryCodeReviewNotFound


class RepositoryCodeReviewService:
    """Generate a repeatable, owner-scoped review of the latest source version."""

    def __init__(
        self,
        repository_catalog: RepositoryCatalog,
        analysis_store: RepositoryAnalysisStore,
        review_store: RepositoryCodeReviewStore,
        storage: RepositoryStorage,
        reviewer: RepositoryCodeReviewer,
    ) -> None:
        self._repository_catalog = repository_catalog
        self._analysis_store = analysis_store
        self._review_store = review_store
        self._storage = storage
        self._reviewer = reviewer

    async def review_latest(
        self, owner_id: UUID, repository_id: UUID
    ) -> RepositoryCodeReviewRecord:
        """Review the latest analyzed repository version and persist the findings."""
        _repository, version = await self._latest_analyzed_version(owner_id, repository_id)
        source_root = self._storage.resolve_storage_key(version.storage_key)
        payload = await asyncio.to_thread(self._reviewer.review, source_root)
        return await self._review_store.upsert(version.id, payload)

    async def get_latest(self, owner_id: UUID, repository_id: UUID) -> RepositoryCodeReviewRecord:
        """Return the saved review for the latest immutable repository version."""
        _repository, version = await self._latest_analyzed_version(owner_id, repository_id)
        review = await self._review_store.get_by_version(version.id)
        if review is None:
            raise RepositoryCodeReviewNotFound
        return review

    async def _latest_analyzed_version(self, owner_id: UUID, repository_id: UUID):
        repository = await self._repository_catalog.get_by_owner(owner_id, repository_id)
        if repository is None:
            raise RepositoryNotFound
        if not repository.versions:
            raise RepositoryAnalysisNotFound
        version = repository.versions[0]
        if await self._analysis_store.get_by_version(version.id) is None:
            raise RepositoryAnalysisNotFound
        return repository, version
