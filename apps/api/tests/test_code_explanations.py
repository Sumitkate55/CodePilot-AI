"""Explain-code endpoint tests without calling a live AI provider."""

from __future__ import annotations

from io import BytesIO
from uuid import UUID
from zipfile import ZipFile

from httpx import AsyncClient

from codepilot_api.domain.explanations.entities import (
    CodeExplanationContext,
    CodeExplanationPayload,
)

VALID_PASSWORD = "SecureCodePilot9"


class StubCodeExplanationAgent:
    """Return a stable explanation and retain the source evidence supplied by the service."""

    def __init__(self) -> None:
        self.contexts: list[CodeExplanationContext] = []

    async def explain(self, context: CodeExplanationContext) -> CodeExplanationPayload:
        self.contexts.append(context)
        return CodeExplanationPayload(
            model="test-explainer",
            content={
                "purpose": "Creates an application instance.",
                "inputs": [],
                "outputs": ["A FastAPI application."],
                "dependencies": ["FastAPI"],
                "logic": ["Instantiates and returns FastAPI."],
                "limitations": ["Only the selected function was analyzed."],
            },
        )


def repository_zip() -> bytes:
    """Build an analyzable repository archive containing one Python function."""
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "project/app/main.py",
            "from fastapi import FastAPI\n\n\ndef create_app() -> FastAPI:\n    return FastAPI()\n",
        )
        archive.writestr("project/requirements.txt", "fastapi==0.115.0\n")
    return buffer.getvalue()


async def authenticated_headers(client: AsyncClient) -> dict[str, str]:
    """Register an isolated test user and return an access token."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "Explain Owner",
            "email": "explain@example.com",
            "password": VALID_PASSWORD,
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_explain_code_uses_only_a_detected_function(app, client: AsyncClient) -> None:
    """A saved analysis gates selected function explanations and preserves source boundaries."""
    agent = StubCodeExplanationAgent()
    app.state.code_explanation_agent = agent
    headers = await authenticated_headers(client)
    upload = await client.post(
        "/api/v1/repositories/upload",
        headers=headers,
        data={"repository_name": "Explain Demo"},
        files={"file": ("explain-demo.zip", repository_zip(), "application/zip")},
    )
    assert upload.status_code == 201
    repository_id = upload.json()["id"]

    missing = await client.get(f"/api/v1/repositories/{repository_id}/functions", headers=headers)
    analysis = await client.post(f"/api/v1/repositories/{repository_id}/analyze", headers=headers)
    functions = await client.get(f"/api/v1/repositories/{repository_id}/functions", headers=headers)
    explanation = await client.post(
        f"/api/v1/repositories/{repository_id}/explain-code",
        headers=headers,
        json={"path": "app/main.py", "line": 4},
    )
    invalid = await client.post(
        f"/api/v1/repositories/{repository_id}/explain-code",
        headers=headers,
        json={"path": "app/main.py", "line": 999},
    )

    assert missing.status_code == 404
    assert analysis.status_code == 200
    assert functions.status_code == 200
    assert functions.json() == [
        {"name": "create_app", "path": "app/main.py", "line": 4, "language": "Python"}
    ]
    assert explanation.status_code == 200
    assert explanation.json()["model"] == "test-explainer"
    assert explanation.json()["function"]["name"] == "create_app"
    assert explanation.json()["content"]["dependencies"] == ["FastAPI"]
    assert invalid.status_code == 404
    assert invalid.json()["error"]["code"] == "function_not_found"
    assert len(agent.contexts) == 1
    assert agent.contexts[0].function.path == "app/main.py"
    assert "def create_app" in agent.contexts[0].source
    assert "requirements.txt" not in agent.contexts[0].source
    assert isinstance(agent.contexts[0].repository_version_id, UUID)
