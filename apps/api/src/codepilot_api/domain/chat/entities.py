"""Framework-independent repository RAG records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class RepositoryChatIndexStatus(StrEnum):
    """Persistent indexing state for one immutable source version."""

    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class RepositoryChunk:
    """A bounded source fragment eligible for embedding and retrieval."""

    id: UUID
    repository_version_id: UUID
    path: str
    start_line: int
    end_line: int
    content: str


@dataclass(frozen=True, slots=True)
class RepositoryChatIndexRecord:
    """Persisted state for the vectors belonging to one source version."""

    id: UUID
    repository_version_id: UUID
    indexing_version: int
    status: RepositoryChatIndexStatus
    embedding_model: str
    chunk_count: int
    indexed_at: datetime | None
    failure_message: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class RetrievedSource:
    """One Qdrant result available as evidence for a repository answer."""

    chunk: RepositoryChunk
    score: float


@dataclass(frozen=True, slots=True)
class RepositoryChatCitation:
    """Safe client-facing source reference for one grounded answer."""

    source_id: str
    path: str
    start_line: int
    end_line: int
    score: float
    excerpt: str


@dataclass(frozen=True, slots=True)
class RepositoryChatAnswer:
    """A source-grounded repository answer and the evidence that supports it."""

    answer: str
    citations: tuple[RepositoryChatCitation, ...]
    grounded: bool
    model: str | None
