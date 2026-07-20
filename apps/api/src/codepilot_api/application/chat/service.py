"""Repository RAG indexing, retrieval, and source-grounded chat use cases."""

from __future__ import annotations

import asyncio
from dataclasses import replace

from codepilot_api.application.chat.contracts import (
    EmbeddingProvider,
    GroundedChatAgent,
    RepositoryChatIndexStore,
    RepositoryChunker,
    RepositoryVectorStore,
)
from codepilot_api.application.repositories.contracts import RepositoryCatalog, RepositoryStorage
from codepilot_api.domain.chat.entities import (
    RepositoryChatAnswer,
    RepositoryChatCitation,
    RepositoryChatIndexRecord,
    RepositoryChatIndexStatus,
)
from codepilot_api.domain.chat.errors import (
    RepositoryChatConfigurationError,
    RepositoryChatIndexingError,
    RepositoryChatNotIndexed,
)
from codepilot_api.domain.repositories.errors import RepositoryNotFound

RAG_INDEXING_VERSION = 1
UNSUPPORTED_ANSWER = "I can’t answer that from the indexed repository context."


class RepositoryChatService:
    """Keep every repository chat answer bounded by the latest indexed source version."""

    def __init__(
        self,
        repository_catalog: RepositoryCatalog,
        index_store: RepositoryChatIndexStore,
        storage: RepositoryStorage,
        chunker: RepositoryChunker,
        embeddings: EmbeddingProvider,
        vector_store: RepositoryVectorStore,
        agent: GroundedChatAgent,
        embedding_model: str,
        search_limit: int,
        min_score: float,
    ) -> None:
        self._repository_catalog = repository_catalog
        self._index_store = index_store
        self._storage = storage
        self._chunker = chunker
        self._embeddings = embeddings
        self._vector_store = vector_store
        self._agent = agent
        self._embedding_model = embedding_model
        self._search_limit = search_limit
        self._min_score = min_score

    async def index_latest(self, owner_id, repository_id) -> RepositoryChatIndexRecord:
        """Replace vectors for the latest immutable source version with safe text chunks."""
        repository = await self._get_repository(owner_id, repository_id)
        version = self._latest_version(repository)
        try:
            source_root = self._storage.resolve_storage_key(version.storage_key)
            chunks = await asyncio.to_thread(self._chunker.chunk, source_root, version.id)
            if not chunks:
                raise RepositoryChatIndexingError(
                    "No safe text files were available to index in this repository version."
                )
            vectors = await self._embeddings.embed([chunk.content for chunk in chunks])
            if len(vectors) != len(chunks):
                raise RepositoryChatIndexingError(
                    "The embedding provider returned incomplete results."
                )
            await self._vector_store.replace_version(version.id, chunks, vectors)
        except (RepositoryChatConfigurationError, RepositoryChatIndexingError) as error:
            await self._index_store.mark_failed(
                version.id, RAG_INDEXING_VERSION, self._embedding_model, str(error)
            )
            raise
        except Exception as error:
            message = "CodePilot could not index this repository for chat. Please try again."
            await self._index_store.mark_failed(
                version.id, RAG_INDEXING_VERSION, self._embedding_model, message
            )
            raise RepositoryChatIndexingError(message) from error
        return await self._index_store.mark_ready(
            version.id, RAG_INDEXING_VERSION, self._embedding_model, len(chunks)
        )

    async def get_index_latest(self, owner_id, repository_id) -> RepositoryChatIndexRecord:
        """Return status for the latest source version only."""
        repository = await self._get_repository(owner_id, repository_id)
        version = self._latest_version(repository)
        index = await self._index_store.get_by_version(version.id)
        if index is None:
            raise RepositoryChatNotIndexed
        if index.embedding_model != self._embedding_model:
            return replace(
                index,
                status=RepositoryChatIndexStatus.FAILED,
                chunk_count=0,
                indexed_at=None,
                failure_message="The configured embedding model changed. Reindex this repository.",
            )
        return index

    async def ask(self, owner_id, repository_id, question: str) -> RepositoryChatAnswer:
        """Answer a user question only when retrieved evidence supports it."""
        repository = await self._get_repository(owner_id, repository_id)
        version = self._latest_version(repository)
        index = await self._index_store.get_by_version(version.id)
        if (
            index is None
            or index.status != RepositoryChatIndexStatus.READY
            or index.embedding_model != self._embedding_model
        ):
            raise RepositoryChatNotIndexed
        vectors = await self._embeddings.embed([question])
        if len(vectors) != 1:
            raise RepositoryChatIndexingError("The embedding provider did not embed the question.")
        sources = await self._vector_store.search(version.id, vectors[0], self._search_limit)
        grounded_sources = tuple(source for source in sources if source.score >= self._min_score)
        if not grounded_sources:
            return RepositoryChatAnswer(
                answer=UNSUPPORTED_ANSWER, citations=(), grounded=False, model=None
            )
        answer, cited_source_ids, model = await self._agent.answer(question, grounded_sources)
        source_by_id = {str(source.chunk.id): source for source in grounded_sources}
        cited_sources = tuple(
            source_by_id[source_id]
            for source_id in dict.fromkeys(cited_source_ids)
            if source_id in source_by_id
        )
        if not cited_sources:
            return RepositoryChatAnswer(
                answer=UNSUPPORTED_ANSWER, citations=(), grounded=False, model=model
            )
        return RepositoryChatAnswer(
            answer=answer,
            citations=tuple(self._citation(source) for source in cited_sources),
            grounded=True,
            model=model,
        )

    async def _get_repository(self, owner_id, repository_id):
        repository = await self._repository_catalog.get_by_owner(owner_id, repository_id)
        if repository is None:
            raise RepositoryNotFound
        return repository

    @staticmethod
    def _latest_version(repository):
        if not repository.versions:
            raise RepositoryChatNotIndexed
        return repository.versions[0]

    @staticmethod
    def _citation(source) -> RepositoryChatCitation:
        excerpt = source.chunk.content[:600].rstrip()
        return RepositoryChatCitation(
            source_id=str(source.chunk.id),
            path=source.chunk.path,
            start_line=source.chunk.start_line,
            end_line=source.chunk.end_line,
            score=round(source.score, 4),
            excerpt=excerpt,
        )
