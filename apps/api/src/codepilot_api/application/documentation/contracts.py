"""Ports for repository documentation generation and persistence."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from codepilot_api.domain.documentation.entities import (
    DocumentationContext,
    DocumentationPayload,
    DocumentationRecord,
)


class DocumentationAgent(Protocol):
    """Generate five Markdown documents from bounded repository intelligence."""

    async def generate(self, context: DocumentationContext) -> DocumentationPayload: ...


class DocumentationStore(Protocol):
    """Persist one current documentation bundle for every immutable source version."""

    async def get_by_version(self, repository_version_id: UUID) -> DocumentationRecord | None: ...

    async def upsert(
        self, repository_version_id: UUID, payload: DocumentationPayload
    ) -> DocumentationRecord: ...
