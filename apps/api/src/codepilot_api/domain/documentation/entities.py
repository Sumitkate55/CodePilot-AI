"""Source-grounded repository documentation records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DocumentationContext:
    """Bounded repository metadata submitted to a documentation provider."""

    repository_id: UUID
    repository_version_id: UUID
    repository_name: str
    source_type: str
    remote_url: str | None
    analysis_results: dict[str, object]


@dataclass(frozen=True, slots=True)
class DocumentationPayload:
    """Five complete Markdown documents generated for one source version."""

    model: str
    prompt_version: int
    documents: dict[str, str]
    notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DocumentationRecord:
    """Persisted documentation bundle attached to an immutable repository version."""

    id: UUID
    repository_version_id: UUID
    model: str
    prompt_version: int
    documents: dict[str, str]
    notes: tuple[str, ...]
    created_at: datetime
    updated_at: datetime
