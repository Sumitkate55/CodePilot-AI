"""Unit-test generator endpoint and framework-selection tests without a live provider."""

from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

from httpx import AsyncClient

from codepilot_api.application.test_generation.service import UnitTestGenerationService
from codepilot_api.domain.test_generation.entities import (
    GeneratedTestPayload,
    UnitTestFramework,
)
from codepilot_api.domain.test_generation.entities import (
    TestCoverageKind as CoverageKind,
)
from codepilot_api.domain.test_generation.entities import (
    TestGenerationContext as GenerationContext,
)

VALID_PASSWORD = "SecureCodePilot9"


class StubUnitTestGenerationAgent:
    """Return a deterministic complete pytest suite and retain its source evidence."""

    def __init__(self) -> None:
        self.contexts: list[GenerationContext] = []

    async def generate(self, context: GenerationContext) -> GeneratedTestPayload:
        self.contexts.append(context)
        return GeneratedTestPayload(
            model="test-unit-generator",
            summary="Covers normalization behavior using source-backed expectations.",
            test_code=(
                "import pytest\n\n\n"
                "def test_normalize_happy_path():\n"
                "    assert normalize('  codepilot  ') == 'codepilot'\n\n\n"
                "def test_normalize_edge_case():\n"
                "    assert normalize('') == ''\n\n\n"
                "def test_normalize_invalid_input():\n"
                "    with pytest.raises(ValueError):\n"
                "        normalize(None)\n\n\n"
                "def test_normalize_boundary_input():\n"
                "    assert normalize(' ') == ''\n"
            ),
            coverage=tuple(CoverageKind),
            notes=("The suite imports normalize from its source module.",),
        )


def repository_zip() -> bytes:
    """Build a source archive with a safe test target and an excluded environment file."""
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "project/app/normalizer.py",
            "def normalize(value: str) -> str:\n"
            "    if not isinstance(value, str):\n"
            "        raise ValueError('value must be a string')\n"
            "    return value.strip()\n",
        )
        archive.writestr("project/.env", "SECRET=never-send-this")
    return buffer.getvalue()


async def authenticated_headers(client: AsyncClient) -> dict[str, str]:
    """Register an isolated owner and return bearer authentication headers."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "Test Generator Owner",
            "email": "tests@example.com",
            "password": VALID_PASSWORD,
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_test_generator_requires_analysis_and_persists_source_grounded_suite(
    app, client: AsyncClient
) -> None:
    """A detected function is the only valid target and its suite is persisted by version."""
    agent = StubUnitTestGenerationAgent()
    app.state.unit_test_generation_agent = agent
    headers = await authenticated_headers(client)
    upload = await client.post(
        "/api/v1/repositories/upload",
        headers=headers,
        data={"repository_name": "Test Generator Demo"},
        files={"file": ("test-generator-demo.zip", repository_zip(), "application/zip")},
    )
    assert upload.status_code == 201
    repository_id = upload.json()["id"]

    missing_analysis = await client.get(
        f"/api/v1/repositories/{repository_id}/test-generation", headers=headers
    )
    analysis = await client.post(f"/api/v1/repositories/{repository_id}/analyze", headers=headers)
    dashboard = await client.get(
        f"/api/v1/repositories/{repository_id}/test-generation", headers=headers
    )
    assert missing_analysis.status_code == 404
    assert missing_analysis.json()["error"]["code"] == "repository_analysis_not_found"
    assert analysis.status_code == 200
    assert dashboard.status_code == 200

    target = next(
        item for item in dashboard.json()["targets"] if item["function"]["name"] == "normalize"
    )
    generated = await client.post(
        f"/api/v1/repositories/{repository_id}/test-generation",
        headers=headers,
        json={"path": target["function"]["path"], "line": target["function"]["line"]},
    )
    persisted = await client.get(
        f"/api/v1/repositories/{repository_id}/test-generation", headers=headers
    )

    assert target["framework"] == "pytest"
    assert generated.status_code == 200
    assert generated.json()["test_path"] == "tests/test_normalizer.py"
    assert "test_normalize_invalid_input" in generated.json()["test_code"]
    assert set(generated.json()["coverage"]) == {kind.value for kind in CoverageKind}
    assert len(persisted.json()["generated_tests"]) == 1
    assert len(agent.contexts) == 1
    assert "def normalize" in agent.contexts[0].source
    assert "never-send-this" not in agent.contexts[0].source


def test_framework_mapping_supports_pytest_jest_and_junit() -> None:
    """Detected Python, JavaScript, TypeScript, and Java symbols select the expected runner."""
    targets = UnitTestGenerationService._supported_functions(
        {
            "symbols": {
                "functions": [
                    {
                        "name": "python_target",
                        "path": "app.py",
                        "line": 1,
                        "language": "Python",
                    },
                    {
                        "name": "javascriptTarget",
                        "path": "app.js",
                        "line": 2,
                        "language": "JavaScript",
                    },
                    {
                        "name": "typeScriptTarget",
                        "path": "app.ts",
                        "line": 3,
                        "language": "TypeScript",
                    },
                    {
                        "name": "javaTarget",
                        "path": "App.java",
                        "line": 4,
                        "language": "Java",
                    },
                    {
                        "name": "ignored",
                        "path": "main.go",
                        "line": 5,
                        "language": "Go",
                    },
                ]
            }
        }
    )

    assert [(function.name, framework) for function, framework in targets] == [
        ("python_target", UnitTestFramework.PYTEST),
        ("javascriptTarget", UnitTestFramework.JEST),
        ("typeScriptTarget", UnitTestFramework.JEST),
        ("javaTarget", UnitTestFramework.JUNIT),
    ]
