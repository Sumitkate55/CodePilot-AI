"""Refactoring-advisor endpoint tests without a live AI provider."""

from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

from httpx import AsyncClient

from codepilot_api.domain.refactoring.entities import (
    RefactoringContext,
    RefactorProposalPayload,
    RefactorRisk,
)

VALID_PASSWORD = "SecureCodePilot9"


class StubRefactoringAgent:
    """Return a predictable proposal while retaining the exact source context received."""

    def __init__(self) -> None:
        self.contexts: list[RefactoringContext] = []

    async def propose(self, context: RefactoringContext) -> RefactorProposalPayload:
        self.contexts.append(context)
        return RefactorProposalPayload(
            model="test-refactor-agent",
            title="Replace dynamic evaluation",
            rationale="Converting to int avoids executing arbitrary expressions.",
            replacement_source=context.source.replace("eval(value)", "int(value)"),
            risk=RefactorRisk.LOW,
            confidence=94,
            estimated_quality_gain=20,
            impact_summary=("Removes dynamic execution from the selected code path.",),
            testing_steps=("Test valid and invalid numeric input.",),
        )


def repository_zip() -> bytes:
    """Build a repository with a reviewable dynamic-code-execution finding."""
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "project/app/unsafe.py",
            "def parse_value(value):\n    return eval(value)\n",
        )
        archive.writestr("project/.env", "SECRET=never-read")
    return buffer.getvalue()


async def authenticated_headers(client: AsyncClient) -> dict[str, str]:
    """Register an isolated user and return bearer authentication headers."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "Refactor Owner",
            "email": "refactor@example.com",
            "password": VALID_PASSWORD,
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_refactoring_advisor_generates_diff_and_persists_decision(
    app, client: AsyncClient
) -> None:
    """The advisor is review-gated, source-grounded, and decision-aware."""
    agent = StubRefactoringAgent()
    app.state.refactoring_agent = agent
    headers = await authenticated_headers(client)
    upload = await client.post(
        "/api/v1/repositories/upload",
        headers=headers,
        data={"repository_name": "Refactor Demo"},
        files={"file": ("refactor-demo.zip", repository_zip(), "application/zip")},
    )
    assert upload.status_code == 201
    repository_id = upload.json()["id"]

    missing_analysis = await client.get(
        f"/api/v1/repositories/{repository_id}/refactoring", headers=headers
    )
    analysis = await client.post(f"/api/v1/repositories/{repository_id}/analyze", headers=headers)
    missing_review = await client.get(
        f"/api/v1/repositories/{repository_id}/refactoring", headers=headers
    )
    review = await client.post(f"/api/v1/repositories/{repository_id}/review", headers=headers)
    finding = next(
        item for item in review.json()["findings"] if item["title"] == "Dynamic code execution"
    )
    initial_dashboard = await client.get(
        f"/api/v1/repositories/{repository_id}/refactoring", headers=headers
    )
    proposal = await client.post(
        f"/api/v1/repositories/{repository_id}/refactoring/proposals",
        headers=headers,
        json={"finding_key": finding["key"]},
    )
    accepted = await client.patch(
        f"/api/v1/repositories/{repository_id}/refactoring/proposals/{proposal.json()['id']}",
        headers=headers,
        json={"status": "accepted"},
    )
    final_dashboard = await client.get(
        f"/api/v1/repositories/{repository_id}/refactoring", headers=headers
    )

    assert missing_analysis.status_code == 404
    assert missing_analysis.json()["error"]["code"] == "repository_analysis_not_found"
    assert analysis.status_code == 200
    assert missing_review.status_code == 404
    assert missing_review.json()["error"]["code"] == "repository_code_review_not_found"
    assert review.status_code == 200
    assert initial_dashboard.status_code == 200
    assert initial_dashboard.json()["proposals"] == []
    assert proposal.status_code == 200
    assert "--- a/app/unsafe.py" in proposal.json()["diff"]
    assert "-    return eval(value)" in proposal.json()["diff"]
    assert "+    return int(value)" in proposal.json()["diff"]
    assert proposal.json()["estimated_quality_gain"] == 10
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"
    assert final_dashboard.status_code == 200
    assert final_dashboard.json()["score"]["accepted_count"] == 1
    assert final_dashboard.json()["score"]["current"] > final_dashboard.json()["score"]["baseline"]
    assert len(agent.contexts) == 1
    assert "eval(value)" in agent.contexts[0].source
    assert ".env" not in agent.contexts[0].source
