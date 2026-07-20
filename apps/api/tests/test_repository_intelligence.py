"""End-to-end repository intelligence tests."""

from __future__ import annotations

import json
from io import BytesIO
from zipfile import ZipFile

from httpx import AsyncClient

VALID_PASSWORD = "SecureCodePilot9"


def repository_zip(entries: dict[str, str]) -> bytes:
    """Build a representative repository archive entirely in memory."""
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for path, content in entries.items():
            archive.writestr(path, content)
    return buffer.getvalue()


async def authenticated_headers(client: AsyncClient) -> dict[str, str]:
    """Register a repository owner and return their bearer token."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "Intelligence Owner",
            "email": "intelligence@example.com",
            "password": VALID_PASSWORD,
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def upload_source_repository(
    client: AsyncClient, headers: dict[str, str]
) -> dict[str, object]:
    """Upload a source tree containing common language, framework, and deployment signals."""
    archive = repository_zip(
        {
            "codepilot/package.json": json.dumps(
                {
                    "dependencies": {"express": "^5.0.0", "react": "^19.0.0"},
                    "devDependencies": {"vite": "^6.0.0"},
                }
            ),
            "codepilot/requirements.txt": "fastapi==0.115.0\nsqlalchemy>=2.0\n",
            "codepilot/src/App.jsx": (
                "import React from 'react';\n\n"
                "export class App extends React.Component {}\n"
                "export function greeting(name) { return `Hi ${name}`; }\n"
            ),
            "codepilot/backend/main.py": (
                "from fastapi import FastAPI\n\n"
                "class ApplicationFactory:\n"
                "    pass\n\n"
                "def create_app() -> FastAPI:\n"
                "    return FastAPI()\n"
            ),
            "codepilot/services/user_service.py": (
                "class UserService:\n"
                "    pass\n\n"
                "async def list_users() -> list[str]:\n"
                "    return []\n"
            ),
            "codepilot/migrations/001_create_users.sql": (
                "CREATE TABLE users (id INTEGER PRIMARY KEY);\n"
            ),
            "codepilot/.env.example": "DATABASE_URL=not-read-by-analysis\n",
            "codepilot/Dockerfile": "FROM python:3.12-slim\n",
            "codepilot/docker-compose.yml": "services:\n  api:\n    build: .\n",
        }
    )
    response = await client.post(
        "/api/v1/repositories/upload",
        headers=headers,
        data={"repository_name": "Intelligence Demo"},
        files={"file": ("intelligence-demo.zip", archive, "application/zip")},
    )
    assert response.status_code == 201
    return response.json()


async def test_repository_analysis_detects_and_persists_source_intelligence(
    client: AsyncClient,
) -> None:
    """Analysis detects source signals and retrieves the saved latest-version result."""
    headers = await authenticated_headers(client)
    repository = await upload_source_repository(client, headers)
    repository_id = repository["id"]

    missing = await client.get(f"/api/v1/repositories/{repository_id}/analysis", headers=headers)
    analysis = await client.post(f"/api/v1/repositories/{repository_id}/analyze", headers=headers)
    persisted = await client.get(f"/api/v1/repositories/{repository_id}/analysis", headers=headers)

    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "repository_analysis_not_found"
    assert analysis.status_code == 200
    assert persisted.status_code == 200

    body = analysis.json()
    results = body["results"]
    languages = {language["name"] for language in results["languages"]}
    class_names = {symbol["name"] for symbol in results["symbols"]["classes"]}
    function_names = {symbol["name"] for symbol in results["symbols"]["functions"]}

    assert body["repository_version_id"] == repository["versions"][0]["id"]
    assert body["file_count"] == 9
    assert body["line_count"] >= 14
    assert {"Python", "JavaScript", "SQL"}.issubset(languages)
    assert {"FastAPI", "React", "Express"}.issubset(set(results["frameworks"]))
    assert {"ApplicationFactory", "App", "UserService"}.issubset(class_names)
    assert {"create_app", "greeting", "list_users"}.issubset(function_names)
    assert results["environment_files"] == [".env.example"]
    assert results["docker_files"] == ["Dockerfile", "docker-compose.yml"]
    assert any(service["path"] == "services/user_service.py" for service in results["services"])
    assert any(
        artifact["path"] == "migrations/001_create_users.sql" and artifact["reason"] == "sql_file"
        for artifact in results["database_artifacts"]
    )
    assert persisted.json()["id"] == body["id"]


async def test_repository_architecture_graph_and_safe_file_preview(client: AsyncClient) -> None:
    """The graph uses saved analysis and opens only bounded non-sensitive repository files."""
    headers = await authenticated_headers(client)
    repository = await upload_source_repository(client, headers)
    repository_id = repository["id"]

    missing = await client.get(
        f"/api/v1/repositories/{repository_id}/architecture-graph", headers=headers
    )
    await client.post(f"/api/v1/repositories/{repository_id}/analyze", headers=headers)
    graph = await client.get(
        f"/api/v1/repositories/{repository_id}/architecture-graph", headers=headers
    )
    source_file = await client.get(
        f"/api/v1/repositories/{repository_id}/files/services/user_service.py", headers=headers
    )
    environment_file = await client.get(
        f"/api/v1/repositories/{repository_id}/files/.env.example", headers=headers
    )

    assert missing.status_code == 404
    assert graph.status_code == 200
    assert {node["kind"] for node in graph.json()["nodes"]} >= {
        "repository",
        "frontend",
        "backend",
        "service",
        "database",
        "infrastructure",
    }
    assert source_file.status_code == 200
    assert source_file.json()["path"] == "services/user_service.py"
    assert "class UserService" in source_file.json()["content"]
    assert environment_file.status_code == 422
    assert environment_file.json()["error"]["code"] == "repository_file_unavailable"
