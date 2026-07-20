"""Repository RAG endpoint tests without OpenAI or Qdrant network calls."""

from __future__ import annotations

from io import BytesIO
from typing import Any
from zipfile import ZipFile

from httpx import AsyncClient

from codepilot_api.domain.chat.entities import RepositoryChunk, RetrievedSource

VALID_PASSWORD = "SecureCodePilot9"


class FakeEmbeddings:
    """Return fixed embeddings while recording chunk and question inputs."""

    def __init__(self) -> None:
        self.inputs: list[list[str]] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.inputs.append(texts)
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeVectorStore:
    """In-memory vector store preserving repository-version scoping for endpoint tests."""

    def __init__(self) -> None:
        self.chunks: dict[str, tuple[RepositoryChunk, ...]] = {}
        self.empty_search = False

    async def replace_version(
        self,
        repository_version_id,
        chunks: tuple[RepositoryChunk, ...],
        vectors: list[list[float]],
    ) -> None:
        assert len(chunks) == len(vectors)
        self.chunks[str(repository_version_id)] = chunks

    async def search(self, repository_version_id, vector: list[float], limit: int):
        if self.empty_search:
            return ()
        return tuple(
            RetrievedSource(chunk=chunk, score=0.92)
            for chunk in self.chunks[str(repository_version_id)][:limit]
        )


class FakeGroundedChatAgent:
    """Return an answer cited to the first supplied retrieved source."""

    async def answer(self, question: str, sources: tuple[RetrievedSource, ...]):
        return (
            "The application entry point is defined in the cited source.",
            (str(sources[0].chunk.id),),
            "test-chat-model",
        )


def repository_zip(entries: dict[str, str]) -> bytes:
    """Build a repository ZIP archive in memory."""
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for path, content in entries.items():
            archive.writestr(path, content)
    return buffer.getvalue()


async def authenticated_headers(client: AsyncClient) -> dict[str, str]:
    """Register a user and return its access token."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "Chat Owner",
            "email": "chat@example.com",
            "password": VALID_PASSWORD,
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def upload_repository(client: AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    """Upload source plus an environment file that must never be embedded."""
    archive = repository_zip(
        {
            "project/app/main.py": "def create_app():\n    return 'ready'\n",
            "project/README.md": "Repository chat is grounded in source citations.\n",
            "project/.env": "OPENAI_API_KEY=must-not-be-indexed\n",
        }
    )
    response = await client.post(
        "/api/v1/repositories/upload",
        headers=headers,
        data={"repository_name": "Chat Demo"},
        files={"file": ("chat-demo.zip", archive, "application/zip")},
    )
    assert response.status_code == 201
    return response.json()


async def test_repository_chat_indexes_safe_source_and_returns_citations(
    app, client: AsyncClient
) -> None:
    """Indexing skips secrets and answers only with a retrieved source citation."""
    embeddings = FakeEmbeddings()
    vector_store = FakeVectorStore()
    app.state.repository_chat_embeddings = embeddings
    app.state.repository_chat_vector_store = vector_store
    app.state.repository_chat_agent = FakeGroundedChatAgent()
    headers = await authenticated_headers(client)
    repository = await upload_repository(client, headers)
    repository_id = repository["id"]

    index_response = await client.post(
        f"/api/v1/repositories/{repository_id}/chat/index", headers=headers
    )
    answer_response = await client.post(
        f"/api/v1/repositories/{repository_id}/chat",
        headers=headers,
        json={"question": "Where is the application entry point?"},
    )

    assert index_response.status_code == 200
    assert index_response.json()["status"] == "ready"
    assert index_response.json()["chunk_count"] == 2
    assert answer_response.status_code == 200
    assert answer_response.json()["grounded"] is True
    assert answer_response.json()["citations"][0]["path"] in {"README.md", "app/main.py"}
    assert all("must-not-be-indexed" not in text for texts in embeddings.inputs for text in texts)


async def test_repository_chat_refuses_questions_without_index(client: AsyncClient) -> None:
    """Chat cannot answer from a repository version that has not been indexed."""
    headers = await authenticated_headers(client)
    repository = await upload_repository(client, headers)

    response = await client.post(
        f"/api/v1/repositories/{repository['id']}/chat",
        headers=headers,
        json={"question": "What does this code do?"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "repository_chat_not_indexed"


async def test_repository_chat_refuses_to_answer_without_retrieved_context(
    app, client: AsyncClient
) -> None:
    """A semantic miss must return the deterministic no-context answer without an LLM call."""
    vector_store = FakeVectorStore()
    vector_store.empty_search = True
    app.state.repository_chat_embeddings = FakeEmbeddings()
    app.state.repository_chat_vector_store = vector_store
    app.state.repository_chat_agent = FakeGroundedChatAgent()
    headers = await authenticated_headers(client)
    repository = await upload_repository(client, headers)
    repository_id = repository["id"]
    await client.post(f"/api/v1/repositories/{repository_id}/chat/index", headers=headers)

    response = await client.post(
        f"/api/v1/repositories/{repository_id}/chat",
        headers=headers,
        json={"question": "What is the production deployment region?"},
    )

    assert response.status_code == 200
    assert response.json()["grounded"] is False
    assert response.json()["citations"] == []
    assert "indexed repository context" in response.json()["answer"]
