"""Ollama adapters for local repository embeddings and grounded answers."""

from __future__ import annotations

import json

from codepilot_api.config.settings import Settings
from codepilot_api.domain.chat.entities import RetrievedSource
from codepilot_api.domain.chat.errors import (
    RepositoryChatConfigurationError,
    RepositoryChatGenerationError,
    RepositoryChatIndexingError,
)
from codepilot_api.infrastructure.chat.openai_repository_chat import (
    CHAT_SYSTEM_INSTRUCTIONS,
    MAX_SOURCE_CHARACTERS,
    StructuredGroundedAnswer,
)
from codepilot_api.infrastructure.ollama.client import (
    OllamaClient,
    OllamaResponseError,
    OllamaUnavailableError,
)


class OllamaEmbeddingProvider:
    """Create repository embeddings using a locally running Ollama model."""

    def __init__(self, settings: Settings) -> None:
        self._model = settings.ollama_embedding_model
        self._client = OllamaClient(settings.ollama_base_url, settings.ollama_timeout_seconds)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed source chunks or a query without sending repository data to a cloud provider."""
        try:
            return await self._client.embed(self._model, texts)
        except OllamaUnavailableError as error:
            raise RepositoryChatConfigurationError(str(error)) from error
        except OllamaResponseError as error:
            raise RepositoryChatIndexingError(str(error)) from error


class OllamaGroundedChatAgent:
    """Produce cited answers only from application-provided retrieved source chunks."""

    def __init__(self, settings: Settings) -> None:
        self._model = settings.ollama_chat_model
        self._client = OllamaClient(settings.ollama_base_url, settings.ollama_timeout_seconds)

    async def answer(
        self, question: str, sources: tuple[RetrievedSource, ...]
    ) -> tuple[str, tuple[str, ...], str]:
        """Generate a schema-validated answer whose citations are checked by the service."""
        evidence = [
            {
                "source_id": str(source.chunk.id),
                "path": source.chunk.path,
                "start_line": source.chunk.start_line,
                "end_line": source.chunk.end_line,
                "content": source.chunk.content[:MAX_SOURCE_CHARACTERS],
            }
            for source in sources
        ]
        try:
            result = await self._client.chat_json(
                self._model,
                CHAT_SYSTEM_INSTRUCTIONS,
                "Question: "
                f"{question}\n\nRetrieved repository evidence:\n"
                f"{json.dumps(evidence, ensure_ascii=True, separators=(',', ':'))}",
                StructuredGroundedAnswer,
            )
        except OllamaUnavailableError as error:
            raise RepositoryChatConfigurationError(str(error)) from error
        except OllamaResponseError as error:
            raise RepositoryChatGenerationError(str(error)) from error
        return result.answer, tuple(result.cited_source_ids), f"ollama/{self._model}"
