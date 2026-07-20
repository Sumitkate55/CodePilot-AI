"""Gemini adapters for repository embeddings and strictly grounded answers."""

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
from codepilot_api.infrastructure.gemini.client import (
    GeminiClient,
    GeminiResponseError,
    GeminiUnavailableError,
)


class GeminiEmbeddingProvider:
    """Create private repository embeddings with Gemini's stable text embedding model."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.gemini_api_key
        self._model = settings.gemini_embedding_model
        self._dimensions = settings.gemini_embedding_dimensions
        self._timeout_seconds = settings.gemini_timeout_seconds

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed safe source chunks without exposing credentials to the browser."""
        if self._api_key is None or not self._api_key.get_secret_value():
            raise RepositoryChatConfigurationError(
                "Repository chat requires GEMINI_API_KEY to be configured on the API server."
            )
        client = GeminiClient(self._api_key.get_secret_value(), self._timeout_seconds)
        try:
            return await client.embed(self._model, texts, self._dimensions)
        except GeminiUnavailableError as error:
            raise RepositoryChatConfigurationError(str(error)) from error
        except GeminiResponseError as error:
            raise RepositoryChatIndexingError(str(error)) from error


class GeminiGroundedChatAgent:
    """Generate cited answers limited to application-supplied repository chunks."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.gemini_api_key
        self._model = settings.gemini_generation_model
        self._timeout_seconds = settings.gemini_timeout_seconds

    async def answer(
        self, question: str, sources: tuple[RetrievedSource, ...]
    ) -> tuple[str, tuple[str, ...], str]:
        """Generate one citation-constrained answer using retrieved source only."""
        if self._api_key is None or not self._api_key.get_secret_value():
            raise RepositoryChatConfigurationError(
                "Repository chat requires GEMINI_API_KEY to be configured on the API server."
            )
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
        client = GeminiClient(self._api_key.get_secret_value(), self._timeout_seconds)
        try:
            result = await client.chat_json(
                self._model,
                CHAT_SYSTEM_INSTRUCTIONS,
                "Question: "
                f"{question}\n\nRetrieved repository evidence:\n"
                f"{json.dumps(evidence, ensure_ascii=True, separators=(',', ':'))}",
                StructuredGroundedAnswer,
            )
        except GeminiUnavailableError as error:
            raise RepositoryChatConfigurationError(str(error)) from error
        except GeminiResponseError as error:
            raise RepositoryChatGenerationError(str(error)) from error
        return result.answer, tuple(result.cited_source_ids), f"gemini/{self._model}"
