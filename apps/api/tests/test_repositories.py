"""Repository upload, history, and deletion endpoint tests."""

from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

from httpx import AsyncClient

from codepilot_api.config.settings import Settings

VALID_PASSWORD = "SecureCodePilot9"


def repository_zip(entries: dict[str, str]) -> bytes:
    """Build a minimal ZIP archive entirely in test memory."""
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for path, content in entries.items():
            archive.writestr(path, content)
    return buffer.getvalue()


async def authenticated_headers(client: AsyncClient) -> tuple[dict[str, str], str]:
    """Register one user and return its bearer access header and user identifier."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "Repository Owner",
            "email": "repositories@example.com",
            "password": VALID_PASSWORD,
        },
    )
    assert response.status_code == 201
    body = response.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]["id"]


async def upload_zip(
    client: AsyncClient, headers: dict[str, str], archive: bytes, name: str = "Demo Repository"
) -> dict[str, object]:
    """Upload one archive and return its decoded repository response."""
    response = await client.post(
        "/api/v1/repositories/upload",
        headers=headers,
        data={"repository_name": name},
        files={"file": ("demo-repository.zip", archive, "application/zip")},
    )
    assert response.status_code == 201
    return response.json()


async def test_zip_upload_creates_history_and_can_be_deleted(
    client: AsyncClient, settings: Settings
) -> None:
    """Two uploads under one name create immutable history and deletion clears local storage."""
    headers, user_id = await authenticated_headers(client)
    first = await upload_zip(client, headers, repository_zip({"demo/main.py": "print('one')"}))
    second = await upload_zip(client, headers, repository_zip({"demo/main.py": "print('two')"}))

    repository_id = first["id"]
    stored_repository = settings.repository_storage_root / user_id / repository_id
    history = await client.get(f"/api/v1/repositories/{repository_id}/versions", headers=headers)
    listing = await client.get("/api/v1/repositories", headers=headers)

    assert second["id"] == repository_id
    assert [item["version_number"] for item in history.json()] == [2, 1]
    assert listing.status_code == 200
    assert listing.json()[0]["versions"][0]["file_count"] == 1
    assert stored_repository.exists()

    deletion = await client.delete(f"/api/v1/repositories/{repository_id}", headers=headers)
    missing = await client.get(f"/api/v1/repositories/{repository_id}", headers=headers)

    assert deletion.status_code == 204
    assert missing.status_code == 404
    assert not stored_repository.exists()


async def test_repository_upload_rejects_unsafe_archives_and_invalid_github_urls(
    client: AsyncClient,
) -> None:
    """Intake must reject traversal archives and non-GitHub clone targets before processing."""
    headers, _ = await authenticated_headers(client)
    unsafe_archive = repository_zip({"../outside.py": "unsafe"})

    unsafe_upload = await client.post(
        "/api/v1/repositories/upload",
        headers=headers,
        data={"repository_name": "Unsafe Archive"},
        files={"file": ("unsafe.zip", unsafe_archive, "application/zip")},
    )
    invalid_github = await client.post(
        "/api/v1/repositories/import/github",
        headers=headers,
        json={"github_url": "https://example.com/owner/repository"},
    )

    assert unsafe_upload.status_code == 422
    assert unsafe_upload.json()["error"]["code"] == "invalid_repository_source"
    assert invalid_github.status_code == 422
    assert invalid_github.json()["error"]["code"] == "invalid_repository_source"
