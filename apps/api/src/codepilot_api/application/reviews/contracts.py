"""Ports used by repository code-review use cases."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol
from uuid import UUID

from codepilot_api.domain.reviews.entities import (
    RepositoryCodeReviewPayload,
    RepositoryCodeReviewRecord,
)


class RepositoryCodeReviewer(Protocol):
    """Review a stored source tree without executing source code."""

    def review(self, source_root: Path) -> RepositoryCodeReviewPayload: ...


class RepositoryCodeReviewStore(Protocol):
    """Persist and retrieve one code-review result per immutable source version."""

    async def get_by_version(
        self, repository_version_id: UUID
    ) -> RepositoryCodeReviewRecord | None: ...

    async def upsert(
        self, repository_version_id: UUID, payload: RepositoryCodeReviewPayload
    ) -> RepositoryCodeReviewRecord: ...
