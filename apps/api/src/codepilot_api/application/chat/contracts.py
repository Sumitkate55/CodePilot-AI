"""Ports required by repository RAG use cases."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol
from uuid import UUID

from codepilot_api.domain.chat.entities import (
    RepositoryChatIndexRecord,
    RepositoryChunk,
    RetrievedSource,
)


class RepositoryChunker(Protocol):
    """Split a safe repository source tree into bounded, cited fragments."""

    def chunk(
        self, source_root: Path, repository_version_id: UUID
    ) -> tuple[RepositoryChunk, ...]: ...


class EmbeddingProvider(Protocol):
    """Generate dense embeddings for repository chunks and user questions."""

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class RepositoryVectorStore(Protocol):
    """Persist and semantically search vectors scoped to one source version."""

    async def replace_version(
        self,
        repository_version_id: UUID,
        chunks: tuple[RepositoryChunk, ...],
        vectors: list[list[float]],
    ) -> None: ...

    async def search(
        self, repository_version_id: UUID, vector: list[float], limit: int
    ) -> tuple[RetrievedSource, ...]: ...


class RepositoryChatIndexStore(Protocol):
    """Persist status metadata for one repository-version vector index."""

    async def get_by_version(
        self, repository_version_id: UUID
    ) -> RepositoryChatIndexRecord | None: ...

    async def mark_ready(
        self,
        repository_version_id: UUID,
        indexing_version: int,
        embedding_model: str,
        chunk_count: int,
    ) -> RepositoryChatIndexRecord: ...

    async def mark_failed(
        self,
        repository_version_id: UUID,
        indexing_version: int,
        embedding_model: str,
        failure_message: str,
    ) -> RepositoryChatIndexRecord: ...


class GroundedChatAgent(Protocol):
    """Create an answer solely from retrieved repository sources."""

    async def answer(
        self, question: str, sources: tuple[RetrievedSource, ...]
    ) -> tuple[str, tuple[str, ...], str]: ...
