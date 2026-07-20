"""Local Ollama adapter tests without a running model server."""

from __future__ import annotations

import json as json_module
from uuid import uuid4

import pytest

from codepilot_api.config.settings import AiProvider, Settings
from codepilot_api.domain.chat.entities import RepositoryChunk, RetrievedSource
from codepilot_api.domain.summaries.entities import ProjectSummaryContext
from codepilot_api.infrastructure.chat.ollama_repository_chat import (
    OllamaEmbeddingProvider,
    OllamaGroundedChatAgent,
)
from codepilot_api.infrastructure.chat.qdrant_repository_vector_store import (
    QdrantRepositoryVectorStore,
)
from codepilot_api.infrastructure.ollama import client as ollama_client_module
from codepilot_api.infrastructure.summaries.ollama_project_summary_agent import (
    OllamaProjectSummaryAgent,
)
from codepilot_api.presentation.dependencies import (
    _embedding_model_name,
    _project_summary_agent,
    _repository_chat_agent,
    _repository_chat_embeddings,
)


def summary_content() -> dict[str, object]:
    """Build a schema-valid local summary response."""
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


class FakeResponse:
    """Minimal successful HTTP response double."""

    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class FakeHttpClient:
    """Capture Ollama HTTP requests and return deterministic structured output."""

    calls: list[dict[str, object]] = []

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def post(self, url: str, json: dict[str, object]) -> FakeResponse:
        self.calls.append({"url": url, "json": json})
        if url.endswith("/api/embed"):
            return FakeResponse({"embeddings": [[0.1, 0.2] for _ in json["input"]]})
        return FakeResponse({"message": {"content": json_module.dumps(summary_content())}})


@pytest.fixture
def ollama_settings() -> Settings:
    """Use local provider settings without real credentials."""
    return Settings(
        database_url="sqlite+aiosqlite://",
        ai_provider=AiProvider.OLLAMA,
        ollama_chat_model="qwen2.5-coder:3b",
        ollama_embedding_model="nomic-embed-text",
    )


@pytest.mark.asyncio
async def test_ollama_summary_and_embeddings_use_local_structured_endpoints(
    monkeypatch, ollama_settings: Settings
) -> None:
    """The local provider submits schema-constrained chat and batched embedding requests."""
    FakeHttpClient.calls.clear()
    monkeypatch.setattr(ollama_client_module.httpx, "Client", FakeHttpClient)
    context = ProjectSummaryContext(
        repository_id=uuid4(),
        repository_version_id=uuid4(),
        repository_name="Demo",
        source_type="zip",
        remote_url=None,
        analysis_results={"statistics": {"total_files": 1}},
    )

    summary = await OllamaProjectSummaryAgent(ollama_settings).generate(context)
    vectors = await OllamaEmbeddingProvider(ollama_settings).embed(["first", "second"])

    assert summary.model == "ollama/qwen2.5-coder:3b"
    assert summary.content["overview"]["summary"] == "Grounded summary."
    assert vectors == [[0.1, 0.2], [0.1, 0.2]]
    chat_request, embedding_request = (call["json"] for call in FakeHttpClient.calls)
    assert chat_request["stream"] is False
    assert chat_request["format"] == "json"
    assert "<response_schema>" in chat_request["messages"][1]["content"]
    assert embedding_request["model"] == "nomic-embed-text"


@pytest.mark.asyncio
async def test_ollama_grounded_chat_returns_only_model_citations(
    monkeypatch, ollama_settings: Settings
) -> None:
    """Application code still validates citations against retrieved source IDs after local chat."""
    monkeypatch.setattr(ollama_client_module.httpx, "Client", FakeHttpClient)
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
    response = {
        "answer": "The app is defined in the cited file.",
        "cited_source_ids": [str(source.chunk.id)],
    }

    class ChatResponseClient(FakeHttpClient):
        def post(self, url: str, json: dict[str, object]) -> FakeResponse:
            self.calls.append({"url": url, "json": json})
            return FakeResponse({"message": {"content": json_module.dumps(response)}})

    monkeypatch.setattr(ollama_client_module.httpx, "Client", ChatResponseClient)
    answer, citations, model = await OllamaGroundedChatAgent(ollama_settings).answer(
        "Where?", (source,)
    )

    assert answer == response["answer"]
    assert citations == (str(source.chunk.id),)
    assert model == "ollama/qwen2.5-coder:3b"


def test_ollama_settings_select_local_adapters(ollama_settings: Settings) -> None:
    """Dependency composition selects Ollama for every AI concern when requested."""
    assert isinstance(_project_summary_agent(ollama_settings), OllamaProjectSummaryAgent)
    assert isinstance(_repository_chat_embeddings(ollama_settings), OllamaEmbeddingProvider)
    assert isinstance(_repository_chat_agent(ollama_settings), OllamaGroundedChatAgent)
    assert _embedding_model_name(ollama_settings) == "ollama/nomic-embed-text"


def test_ollama_embeddings_use_a_dedicated_qdrant_collection(ollama_settings: Settings) -> None:
    """Switching providers cannot mix local vectors with existing OpenAI vectors."""
    local_store = QdrantRepositoryVectorStore(ollama_settings, "ollama/nomic-embed-text")
    openai_store = QdrantRepositoryVectorStore(ollama_settings, "text-embedding-3-small")

    assert local_store._collection_name != ollama_settings.qdrant_collection_name
    assert openai_store._collection_name == ollama_settings.qdrant_collection_name
