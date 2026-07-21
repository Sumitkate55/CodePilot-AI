"""Small server-side client for Gemini structured generation and embeddings."""

from __future__ import annotations

import asyncio
import random
import threading
import time
from collections.abc import Mapping
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
MAX_EMBEDDING_BATCH_SIZE = 100
MAX_TRANSIENT_RETRIES = 6
MAX_RETRY_DELAY_SECONDS = 30.0
TRANSIENT_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
# Gemini Free currently limits the generation endpoint to a small request-per-minute
# budget. Keep one API process below that threshold even when different dashboard
# tools are clicked quickly.
GENERATION_REQUEST_INTERVAL_SECONDS = 3.5


class GeminiUnavailableError(Exception):
    """Gemini cannot be reached from the API service."""


class GeminiResponseError(Exception):
    """Gemini returned a response that cannot be used safely."""


class GeminiClient:
    """Call Gemini REST endpoints away from FastAPI's event loop.

    The API key is sent only from the backend in an HTTP header. It is never part of a
    browser response, client-side bundle, log message, or persisted project artifact.
    """

    _generation_request_lock = threading.Lock()
    _next_generation_request_at = 0.0

    def __init__(self, api_key: str, timeout_seconds: int) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def chat_json(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        max_output_tokens: int | None = None,
    ) -> BaseModel:
        """Generate one Pydantic-validated JSON response."""
        return await asyncio.to_thread(
            self._chat_json_sync,
            model,
            system_prompt,
            user_prompt,
            response_schema,
            max_output_tokens,
        )

    async def embed(
        self,
        model: str,
        texts: list[str],
        dimensions: int,
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> list[list[float]]:
        """Create bounded batches of embeddings in the supplied order."""
        if not texts:
            return []
        return await asyncio.to_thread(
            self._embed_sync, model, texts, dimensions, task_type
        )

    def _chat_json_sync(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        max_output_tokens: int | None,
    ) -> BaseModel:
        self._wait_for_generation_slot()
        generation_config: dict[str, Any] = {
            "responseMimeType": "application/json",
            "responseJsonSchema": response_schema.model_json_schema(),
            "temperature": 0.1,
        }
        if max_output_tokens is not None:
            generation_config["maxOutputTokens"] = max_output_tokens
        response = self._post(
            f"/models/{model}:generateContent",
            {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "generationConfig": generation_config,
            },
            model,
        )
        content = self._candidate_text(response)
        try:
            return response_schema.model_validate_json(content)
        except ValidationError as error:
            raise GeminiResponseError(
                "Gemini returned a response with an invalid structure."
            ) from error

    def _embed_sync(
        self, model: str, texts: list[str], dimensions: int, task_type: str
    ) -> list[list[float]]:
        vectors: list[list[float]] = []
        for offset in range(0, len(texts), MAX_EMBEDDING_BATCH_SIZE):
            batch = texts[offset : offset + MAX_EMBEDDING_BATCH_SIZE]
            response = self._post(
                f"/models/{model}:batchEmbedContents",
                {
                    "requests": [
                        {
                            "model": f"models/{model}",
                            "content": {"parts": [{"text": text}]},
                            "embedContentConfig": {
                                "taskType": task_type,
                                "outputDimensionality": dimensions,
                            },
                        }
                        for text in batch
                    ]
                },
                model,
            )
            embeddings = response.get("embeddings")
            if not isinstance(embeddings, list) or len(embeddings) != len(batch):
                raise GeminiResponseError("Gemini returned incomplete embeddings.")
            vectors.extend(self._vectors(embeddings))
        return vectors

    def _post(self, path: str, payload: dict[str, Any], model: str) -> dict[str, Any]:
        for attempt in range(MAX_TRANSIENT_RETRIES + 1):
            try:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    response = client.post(
                        f"{GEMINI_API_BASE_URL}{path}",
                        headers={"x-goog-api-key": self._api_key},
                        json=payload,
                    )
                    if (
                        response.status_code in TRANSIENT_STATUS_CODES
                        and attempt < MAX_TRANSIENT_RETRIES
                    ):
                        time.sleep(self._retry_delay_seconds(response, attempt))
                        continue
                    response.raise_for_status()
            except httpx.ConnectError as error:
                raise GeminiUnavailableError(
                    "Gemini could not be reached from the API server."
                ) from error
            except httpx.TimeoutException as error:
                raise GeminiUnavailableError(
                    "Gemini did not respond before the configured timeout. Please retry."
                ) from error
            except httpx.HTTPStatusError as error:
                if error.response.status_code == httpx.codes.TOO_MANY_REQUESTS:
                    raise GeminiResponseError(
                        "Gemini's free request limit is temporarily reached. Wait about one "
                        "minute, then retry a single AI action."
                    ) from error
                detail = self._error_detail(error.response)
                raise GeminiResponseError(
                    f"Gemini could not use model '{model}'. {detail}"
                ) from error
            except httpx.HTTPError as error:
                raise GeminiUnavailableError(
                    "CodePilot could not communicate with Gemini."
                ) from error
            break
        else:  # pragma: no cover - retained for defensive completeness.
            raise GeminiUnavailableError("Gemini retry attempts were exhausted.")
        try:
            body = response.json()
        except ValueError as error:
            raise GeminiResponseError("Gemini returned a non-JSON response.") from error
        if not isinstance(body, dict):
            raise GeminiResponseError("Gemini returned an invalid response.")
        return body

    @classmethod
    def _wait_for_generation_slot(cls) -> None:
        """Serialize generation calls so the shared free-tier quota is not burst."""
        with cls._generation_request_lock:
            now = time.monotonic()
            scheduled_at = max(now, cls._next_generation_request_at)
            cls._next_generation_request_at = (
                scheduled_at + GENERATION_REQUEST_INTERVAL_SECONDS
            )
        delay = scheduled_at - now
        if delay > 0:
            time.sleep(delay)

    @staticmethod
    def _retry_delay_seconds(response: httpx.Response, attempt: int) -> float:
        """Honor a provider retry hint, then fall back to bounded exponential backoff."""
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                delay = float(retry_after)
            except ValueError:
                delay = 0.0
            if delay > 0:
                return min(delay, MAX_RETRY_DELAY_SECONDS)
        return min(2.0**attempt, MAX_RETRY_DELAY_SECONDS) + random.uniform(0.0, 0.5)

    @staticmethod
    def _candidate_text(response: Mapping[str, Any]) -> str:
        candidates = response.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise GeminiResponseError("Gemini did not return a generated candidate.")
        candidate = candidates[0]
        content = candidate.get("content") if isinstance(candidate, Mapping) else None
        parts = content.get("parts") if isinstance(content, Mapping) else None
        if not isinstance(parts, list):
            raise GeminiResponseError("Gemini returned an empty generated candidate.")
        text = "".join(
            part.get("text", "") for part in parts if isinstance(part, Mapping)
        )
        if not text.strip():
            raise GeminiResponseError("Gemini returned an empty generated candidate.")
        return text

    @staticmethod
    def _vectors(embeddings: list[object]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for embedding in embeddings:
            values = embedding.get("values") if isinstance(embedding, Mapping) else None
            if not isinstance(values, list) or not values:
                raise GeminiResponseError("Gemini returned an invalid embedding vector.")
            try:
                vectors.append([float(value) for value in values])
            except (TypeError, ValueError) as error:
                raise GeminiResponseError("Gemini returned an invalid embedding vector.") from error
        return vectors

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        try:
            error = response.json().get("error")
        except (ValueError, AttributeError):
            error = None
        if isinstance(error, Mapping):
            detail = error.get("message") or error.get("status")
        else:
            detail = error
        return str(detail).strip() if detail else "The provider rejected the request."
