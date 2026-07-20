"""Repository-wide code review endpoint tests."""

from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

from httpx import AsyncClient

VALID_PASSWORD = "SecureCodePilot9"


def repository_zip() -> bytes:
    """Build a source archive containing deterministic review findings."""
    long_body = "\n".join(f"    value += {index}" for index in range(85))
    source = f"""import pickle


def NotSnakeCase(value):
    try:
        return eval(value)
    except:
        return None


def _unused_helper():
    return "unused"


def long_function(value):
{long_body}
    return value


def duplicate_block(value):
    first = value + 1
    second = first + 2
    third = second + 3
    fourth = third + 4
    fifth = fourth + 5
    sixth = fifth + 6
    return sixth
"""
    duplicate_source = """def another_duplicate(value):
    first = value + 1
    second = first + 2
    third = second + 3
    fourth = third + 4
    fifth = fourth + 5
    sixth = fifth + 6
    return sixth
"""
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("project/app/review_target.py", source)
        archive.writestr("project/app/duplicate.py", duplicate_source)
        archive.writestr("project/.env", "SECRET=never-read")
    return buffer.getvalue()


async def authenticated_headers(client: AsyncClient) -> dict[str, str]:
    """Register an isolated test user and return an access token."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "Review Owner",
            "email": "review@example.com",
            "password": VALID_PASSWORD,
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_code_review_requires_analysis_and_returns_actionable_findings(
    client: AsyncClient,
) -> None:
    """Review results are scoped, persisted, and include every requested core category."""
    headers = await authenticated_headers(client)
    upload = await client.post(
        "/api/v1/repositories/upload",
        headers=headers,
        data={"repository_name": "Review Demo"},
        files={"file": ("review-demo.zip", repository_zip(), "application/zip")},
    )
    assert upload.status_code == 201
    repository_id = upload.json()["id"]

    missing = await client.post(f"/api/v1/repositories/{repository_id}/review", headers=headers)
    analysis = await client.post(f"/api/v1/repositories/{repository_id}/analyze", headers=headers)
    generated = await client.post(f"/api/v1/repositories/{repository_id}/review", headers=headers)
    saved = await client.get(f"/api/v1/repositories/{repository_id}/review", headers=headers)

    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "repository_analysis_not_found"
    assert analysis.status_code == 200
    assert generated.status_code == 200
    assert saved.status_code == 200
    assert generated.json()["id"] == saved.json()["id"]
    assert generated.json()["scanned_file_count"] == 2
    assert generated.json()["severity_counts"]["high"] >= 1
    categories = {finding["category"] for finding in generated.json()["findings"]}
    assert {
        "security",
        "naming",
        "dead_code",
        "code_smell",
        "long_function",
        "duplicate_code",
    } <= categories
    finding = next(
        finding for finding in generated.json()["findings"] if finding["category"] == "security"
    )
    assert finding["path"] == "app/review_target.py"
    assert finding["start_line"] > 0
    assert 0 <= finding["confidence"] <= 100
    assert finding["recommendation"]
