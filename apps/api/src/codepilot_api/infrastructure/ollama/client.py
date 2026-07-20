"""Small, provider-neutral client for Ollama's local HTTP API."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError


class OllamaUnavailableError(Exception):
    """Ollama cannot be reached at the configured local address."""


class OllamaResponseError(Exception):
    """Ollama responded, but did not produce a usable model result."""


class OllamaClient:
    """Call local Ollama chat and embedding endpoints outside the event loop."""

    def __init__(self, base_url: str, timeout_seconds: int) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def embed(self, model: str, texts: list[str]) -> list[list[float]]:
        """Create one local embedding per input text."""
        if not texts:
            return []
        return await asyncio.to_thread(self._embed_sync, model, texts)

    async def chat_json(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        num_predict: int | None = None,
    ) -> BaseModel:
        """Generate and validate a non-streaming structured chat response."""
        return await asyncio.to_thread(
            self._chat_json_sync, model, system_prompt, user_prompt, response_schema, num_predict
        )

    def _embed_sync(self, model: str, texts: list[str]) -> list[list[float]]:
        response = self._post(
            "/api/embed",
            {"model": model, "input": texts, "truncate": True},
            model,
        )
        vectors = response.get("embeddings")
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise OllamaResponseError("Ollama returned incomplete embeddings.")
        parsed_vectors: list[list[float]] = []
        for vector in vectors:
            if not isinstance(vector, list) or not vector:
                raise OllamaResponseError("Ollama returned an invalid embedding vector.")
            try:
                parsed_vectors.append([float(value) for value in vector])
            except (TypeError, ValueError) as error:
                raise OllamaResponseError("Ollama returned an invalid embedding vector.") from error
        return parsed_vectors

    def _chat_json_sync(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        num_predict: int | None,
    ) -> BaseModel:
        response = self._post(
            "/api/chat",
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": self._structured_user_prompt(user_prompt, response_schema),
                    },
                ],
                "stream": False,
                # Some compact local models cannot compile full JSON Schema grammars. JSON mode
                # remains provider-enforced, and Pydantic validates the exact schema afterwards.
                "format": "json",
                "options": {
                    "temperature": 0,
                    **({"num_predict": num_predict} if num_predict is not None else {}),
                },
            },
            model,
        )
        message = response.get("message")
        content = message.get("content") if isinstance(message, Mapping) else None
        if not isinstance(content, str) or not content.strip():
            raise OllamaResponseError("Ollama returned an empty structured response.")
        try:
            return response_schema.model_validate_json(content)
        except ValidationError as error:
            raise OllamaResponseError(
                "Ollama returned a response with an invalid structure."
            ) from error

    def _post(self, path: str, payload: dict[str, Any], model: str) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.post(f"{self._base_url}{path}", json=payload)
                response.raise_for_status()
        except httpx.ConnectError as error:
            raise OllamaUnavailableError(
                f"Ollama is not running at {self._base_url}. Open Ollama, then retry."
            ) from error
        except httpx.TimeoutException as error:
            raise OllamaUnavailableError(
                "Ollama did not respond before the configured timeout. "
                "Ensure it is running and retry."
            ) from error
        except httpx.HTTPStatusError as error:
            detail = self._error_detail(error.response)
            guidance = f" Run `ollama pull {model}` if the model is not installed."
            raise OllamaResponseError(
                f"Ollama could not use local model '{model}'. {detail}{guidance}"
            ) from error
        except httpx.HTTPError as error:
            raise OllamaUnavailableError(
                "CodePilot could not communicate with local Ollama."
            ) from error
        try:
            body = response.json()
        except ValueError as error:
            raise OllamaResponseError("Ollama returned a non-JSON response.") from error
        if not isinstance(body, dict):
            raise OllamaResponseError("Ollama returned an invalid response.")
        return body

    @staticmethod
    def _structured_user_prompt(user_prompt: str, response_schema: type[BaseModel]) -> str:
        """State the validation contract in prompt text for JSON-mode local models."""
        schema = json.dumps(
            response_schema.model_json_schema(), ensure_ascii=True, separators=(",", ":")
        )
        return (
            f"{user_prompt}\n\nReturn exactly one valid JSON object that conforms to this schema. "
            "Do not include Markdown, prose outside the JSON object, or additional fields.\n"
            f"<response_schema>{schema}</response_schema>"
        )

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        try:
            detail = response.json().get("error")
        except (ValueError, AttributeError):
            detail = None
        if isinstance(detail, Mapping):
            detail = detail.get("message") or detail.get("error")
        return str(detail).strip() if detail else "The local provider rejected the request."
