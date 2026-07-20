"""Project-summary API tests without calling the live OpenAI service."""

from __future__ import annotations

from io import BytesIO
from typing import Any
from zipfile import ZipFile

from httpx import AsyncClient

from codepilot_api.domain.summaries.entities import ProjectSummaryContext, ProjectSummaryPayload
from codepilot_api.domain.summaries.errors import ProjectSummaryRateLimitedError

VALID_PASSWORD = "SecureCodePilot9"


def repository_zip(entries: dict[str, str]) -> bytes:
    """Build a repository ZIP archive entirely in test memory."""
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for path, content in entries.items():
            archive.writestr(path, content)
    return buffer.getvalue()


def summary_content() -> dict[str, object]:
    """Return a stable structured output used by the in-process summary-agent double."""
    section = {"summary": "Grounded in the scanned repository metadata.", "evidence": ["Python"]}
    return {
        "overview": section,
        "architecture": section,
        "features": section,
        "frontend_flow": section,
        "backend_flow": section,
        "database_flow": section,
        "authentication_flow": section,
        "api_flow": section,
        "limitations": ["Only scanned metadata was available."],
    }


class StubProjectSummaryAgent:
    """Provider-free project-summary agent that records supplied repository evidence."""

    def __init__(self) -> None:
        self.contexts: list[ProjectSummaryContext] = []

    async def generate(self, context: ProjectSummaryContext) -> ProjectSummaryPayload:
        self.contexts.append(context)
        return ProjectSummaryPayload(
            model="test-gpt-5",
            prompt_version=1,
            content=summary_content(),
        )


class RateLimitedProjectSummaryAgent:
    """Provider double that models a temporary OpenAI rate-limit response."""

    async def generate(self, context: ProjectSummaryContext) -> ProjectSummaryPayload:
        raise ProjectSummaryRateLimitedError(retry_after_seconds=45)


async def authenticated_headers(client: AsyncClient) -> dict[str, str]:
    """Register a user and return their bearer access token."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "Summary Owner",
            "email": "summary@example.com",
            "password": VALID_PASSWORD,
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def upload_repository(client: AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    """Upload a minimal, recognizable source tree for project-summary tests."""
    archive = repository_zip(
        {
            "project/backend/main.py": (
                "from fastapi import FastAPI\n\ndef create_app():\n    return FastAPI()\n"
            ),
            "project/requirements.txt": "fastapi==0.115.0\n",
            "project/Dockerfile": "FROM python:3.12-slim\n",
        }
    )
    response = await client.post(
        "/api/v1/repositories/upload",
        headers=headers,
        data={"repository_name": "Summary Demo"},
        files={"file": ("summary-demo.zip", archive, "application/zip")},
    )
    assert response.status_code == 201
    return response.json()


async def test_project_summary_reports_missing_openai_configuration(client: AsyncClient) -> None:
    """A missing server-side key must fail safely without calling an external provider."""
    headers = await authenticated_headers(client)
    repository = await upload_repository(client, headers)

    response = await client.post(
        f"/api/v1/repositories/{repository['id']}/summary", headers=headers
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ai_not_configured"


async def test_project_summary_auto_analyzes_and_persists_latest_version(
    app, client: AsyncClient
) -> None:
    """Summary generation uses analysis evidence, stores its result, and serves it on retrieval."""
    agent = StubProjectSummaryAgent()
    app.state.project_summary_agent = agent
    headers = await authenticated_headers(client)
    repository = await upload_repository(client, headers)
    repository_id = repository["id"]

    summary_response = await client.post(
        f"/api/v1/repositories/{repository_id}/summary", headers=headers
    )
    persisted_response = await client.get(
        f"/api/v1/repositories/{repository_id}/summary", headers=headers
    )
    analysis_response = await client.get(
        f"/api/v1/repositories/{repository_id}/analysis", headers=headers
    )

    assert summary_response.status_code == 200
    assert persisted_response.status_code == 200
    assert analysis_response.status_code == 200
    assert summary_response.json()["model"] == "test-gpt-5"
    assert persisted_response.json()["id"] == summary_response.json()["id"]
    assert summary_response.json()["content"]["overview"]["evidence"] == ["Python"]
    assert len(agent.contexts) == 1
    assert str(agent.contexts[0].repository_version_id) == repository["versions"][0]["id"]
    assert agent.contexts[0].analysis_results["statistics"]["total_files"] == 3


async def test_project_summary_reports_provider_rate_limits(app, client: AsyncClient) -> None:
    """Rate limits must remain actionable without exposing provider response details."""
    app.state.project_summary_agent = RateLimitedProjectSummaryAgent()
    headers = await authenticated_headers(client)
    repository = await upload_repository(client, headers)

    response = await client.post(
        f"/api/v1/repositories/{repository['id']}/summary", headers=headers
    )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "45"
    assert response.json()["error"]["code"] == "ai_rate_limited"
    assert "OpenAI has temporarily rate-limited" in response.json()["error"]["message"]
