"""Gemini adapter tests without contacting the hosted provider."""

from __future__ import annotations

import json as json_module
from uuid import uuid4

import pytest
from pydantic import SecretStr

from codepilot_api.config.settings import AiProvider, Settings
from codepilot_api.domain.chat.entities import RepositoryChunk, RetrievedSource
from codepilot_api.domain.summaries.entities import ProjectSummaryContext
from codepilot_api.infrastructure.chat.gemini_repository_chat import (
    GeminiEmbeddingProvider,
    GeminiGroundedChatAgent,
)
from codepilot_api.infrastructure.gemini import client as gemini_client_module
from codepilot_api.infrastructure.summaries.gemini_project_summary_agent import (
    GeminiProjectSummaryAgent,
)
from codepilot_api.presentation.dependencies import (
    _embedding_model_name,
    _project_summary_agent,
    _repository_chat_agent,
    _repository_chat_embeddings,
)


def _summary_content() -> dict[str, object]:
    section = {"summary": "Grounded summary.", "evidence": ["Python"]}
    return {
        "overview": section,
        "architecture": section,
        "features": section,
        "frontend_flow": section,
        "backend_flow": section,
        "database_flow": section,
        "authentication_flow": section,
        "api_flow": section,
        "limitations": ["Metadata only."],
    }


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class _FakeHttpClient:
    calls: list[dict[str, object]] = []

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def post(
        self, url: str, *, headers: dict[str, str], json: dict[str, object]
    ) -> _FakeResponse:
        self.calls.append({"url": url, "headers": headers, "json": json})
        if url.endswith(":batchEmbedContents"):
            return _FakeResponse(
                {"embeddings": [{"values": [0.1, 0.2]} for _ in json["requests"]]}
            )
        return _FakeResponse(
            {
                "candidates": [
                    {"content": {"parts": [{"text": json_module.dumps(_summary_content())}]}}
                ]
            }
        )


@pytest.fixture
def gemini_settings() -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite://",
        ai_provider=AiProvider.GEMINI,
        gemini_api_key=SecretStr("test-gemini-key"),
        gemini_generation_model="gemini-3.5-flash",
        gemini_embedding_model="gemini-embedding-2",
        gemini_embedding_dimensions=768,
    )


@pytest.mark.asyncio
async def test_gemini_summary_and_embeddings_use_server_side_api(
    monkeypatch, gemini_settings: Settings
) -> None:
    _FakeHttpClient.calls.clear()
    monkeypatch.setattr(gemini_client_module.httpx, "Client", _FakeHttpClient)
    context = ProjectSummaryContext(
        repository_id=uuid4(),
        repository_version_id=uuid4(),
        repository_name="Demo",
        source_type="zip",
        remote_url=None,
        analysis_results={"statistics": {"total_files": 1}},
    )

    summary = await GeminiProjectSummaryAgent(gemini_settings).generate(context)
    vectors = await GeminiEmbeddingProvider(gemini_settings).embed(["first", "second"])

    assert summary.model == "gemini/gemini-3.5-flash"
    assert summary.content["overview"]["summary"] == "Grounded summary."
    assert vectors == [[0.1, 0.2], [0.1, 0.2]]
    generation_call, embedding_call = _FakeHttpClient.calls
    assert generation_call["headers"] == {"x-goog-api-key": "test-gemini-key"}
    assert generation_call["json"]["generationConfig"]["responseMimeType"] == "application/json"
    assert embedding_call["json"]["requests"][0]["embedContentConfig"] == {
        "taskType": "RETRIEVAL_DOCUMENT",
        "outputDimensionality": 768,
    }


@pytest.mark.asyncio
async def test_gemini_grounded_chat_returns_only_model_citations(
    monkeypatch, gemini_settings: Settings
) -> None:
    source = RetrievedSource(
        chunk=RepositoryChunk(
            id=uuid4(),
            repository_version_id=uuid4(),
            path="app/main.py",
            start_line=1,
            end_line=2,
            content="def create_app(): pass",
        ),
        score=0.9,
    )
    answer = {
        "answer": "The app is defined in the cited file.",
        "cited_source_ids": [str(source.chunk.id)],
    }

    class _ChatHttpClient(_FakeHttpClient):
        def post(
            self, url: str, *, headers: dict[str, str], json: dict[str, object]
        ) -> _FakeResponse:
            self.calls.append({"url": url, "headers": headers, "json": json})
            return _FakeResponse(
                {
                    "candidates": [
                        {"content": {"parts": [{"text": json_module.dumps(answer)}]}}
                    ]
                }
            )

    monkeypatch.setattr(gemini_client_module.httpx, "Client", _ChatHttpClient)
    result, citations, model = await GeminiGroundedChatAgent(gemini_settings).answer(
        "Where?", (source,)
    )

    assert result == answer["answer"]
    assert citations == (str(source.chunk.id),)
    assert model == "gemini/gemini-3.5-flash"


def test_gemini_settings_select_gemini_adapters(gemini_settings: Settings) -> None:
    assert isinstance(_project_summary_agent(gemini_settings), GeminiProjectSummaryAgent)
    assert isinstance(_repository_chat_embeddings(gemini_settings), GeminiEmbeddingProvider)
    assert isinstance(_repository_chat_agent(gemini_settings), GeminiGroundedChatAgent)
    assert _embedding_model_name(gemini_settings) == "gemini/gemini-embedding-2/768"


def test_railway_postgres_url_is_normalized_to_asyncpg() -> None:
    settings = Settings(database_url="postgresql://user:password@postgres:5432/codepilot")

    assert settings.database_url == "postgresql+asyncpg://user:password@postgres:5432/codepilot"
