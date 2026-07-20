"""Qdrant adapter for repository-version-scoped embeddings."""

from __future__ import annotations

import asyncio
from hashlib import sha256
from uuid import UUID

from qdrant_client import QdrantClient, models

from codepilot_api.config.settings import Settings
from codepilot_api.domain.chat.entities import RepositoryChunk, RetrievedSource
from codepilot_api.domain.chat.errors import (
    RepositoryChatConfigurationError,
    RepositoryChatIndexingError,
)


class QdrantRepositoryVectorStore:
    """Store source vectors in Qdrant and filter every query to one repository version."""

    def __init__(self, settings: Settings, embedding_model: str | None = None) -> None:
        self._url = settings.qdrant_url
        self._api_key = settings.qdrant_api_key
        self._collection_name = self._collection_name_for_model(
            settings.qdrant_collection_name, embedding_model
        )

    async def replace_version(
        self,
        repository_version_id: UUID,
        chunks: tuple[RepositoryChunk, ...],
        vectors: list[list[float]],
    ) -> None:
        """Atomically replace every vector belonging to one immutable source version."""
        if not chunks or not vectors or len(chunks) != len(vectors):
            raise RepositoryChatIndexingError("Repository chunks and embeddings did not match.")
        await asyncio.to_thread(self._replace_version_sync, repository_version_id, chunks, vectors)

    async def search(
        self, repository_version_id: UUID, vector: list[float], limit: int
    ) -> tuple[RetrievedSource, ...]:
        """Search Qdrant with an ownership-safe repository-version filter."""
        try:
            return await asyncio.to_thread(self._search_sync, repository_version_id, vector, limit)
        except Exception as error:
            raise RepositoryChatIndexingError(
                "CodePilot could not search the repository index. Please try again."
            ) from error

    def _replace_version_sync(
        self,
        repository_version_id: UUID,
        chunks: tuple[RepositoryChunk, ...],
        vectors: list[list[float]],
    ) -> None:
        try:
            client = self._client()
            self._ensure_collection(client, len(vectors[0]))
            source_filter = self._version_filter(repository_version_id)
            client.delete(
                collection_name=self._collection_name,
                points_selector=models.FilterSelector(filter=source_filter),
                wait=True,
            )
            client.upsert(
                collection_name=self._collection_name,
                wait=True,
                points=[
                    models.PointStruct(
                        id=str(chunk.id),
                        vector=vector,
                        payload={
                            "repository_version_id": str(repository_version_id),
                            "path": chunk.path,
                            "start_line": chunk.start_line,
                            "end_line": chunk.end_line,
                            "content": chunk.content,
                        },
                    )
                    for chunk, vector in zip(chunks, vectors, strict=True)
                ],
            )
        except RepositoryChatConfigurationError:
            raise
        except Exception as error:
            raise RepositoryChatIndexingError(
                "CodePilot could not write repository embeddings to Qdrant."
            ) from error

    def _search_sync(
        self, repository_version_id: UUID, vector: list[float], limit: int
    ) -> tuple[RetrievedSource, ...]:
        client = self._client()
        result = client.query_points(
            collection_name=self._collection_name,
            query=vector,
            query_filter=self._version_filter(repository_version_id),
            with_payload=True,
            limit=limit,
        )
        sources: list[RetrievedSource] = []
        for point in result.points:
            payload = point.payload or {}
            try:
                chunk = RepositoryChunk(
                    id=UUID(str(point.id)),
                    repository_version_id=repository_version_id,
                    path=str(payload["path"]),
                    start_line=int(payload["start_line"]),
                    end_line=int(payload["end_line"]),
                    content=str(payload["content"]),
                )
            except (KeyError, TypeError, ValueError):
                continue
            sources.append(RetrievedSource(chunk=chunk, score=float(point.score)))
        return tuple(sources)

    def _client(self) -> QdrantClient:
        if not self._url:
            raise RepositoryChatConfigurationError(
                "Repository chat requires QDRANT_URL to be configured."
            )
        api_key = self._api_key.get_secret_value() if self._api_key else None
        return QdrantClient(url=self._url, api_key=api_key, timeout=30)

    def _ensure_collection(self, client: QdrantClient, vector_size: int) -> None:
        if not client.collection_exists(self._collection_name):
            client.create_collection(
                collection_name=self._collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size, distance=models.Distance.COSINE
                ),
            )
            for field_name in ("repository_version_id",):
                client.create_payload_index(
                    collection_name=self._collection_name,
                    field_name=field_name,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                    wait=True,
                )

    @staticmethod
    def _version_filter(repository_version_id: UUID) -> models.Filter:
        return models.Filter(
            must=[
                models.FieldCondition(
                    key="repository_version_id",
                    match=models.MatchValue(value=str(repository_version_id)),
                )
            ]
        )

    @staticmethod
    def _collection_name_for_model(base_name: str, embedding_model: str | None) -> str:
        """Keep embeddings of incompatible dimensions in separate Qdrant collections."""
        if embedding_model is None or not embedding_model.startswith("ollama/"):
            return base_name
        model_hash = sha256(embedding_model.encode("utf-8")).hexdigest()[:12]
        return f"{base_name}_{model_hash}"
