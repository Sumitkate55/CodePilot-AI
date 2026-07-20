"""OpenAI project-summary adapter tests without network access."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import Request, Response
from openai import RateLimitError

from codepilot_api.config.settings import Settings
from codepilot_api.domain.summaries.entities import ProjectSummaryContext
from codepilot_api.domain.summaries.errors import ProjectSummaryRateLimitedError
from codepilot_api.infrastructure.summaries import openai_project_summary_agent as agent_module
from codepilot_api.infrastructure.summaries.openai_project_summary_agent import (
    OpenAIProjectSummaryAgent,
    StructuredProjectSummary,
)


def structured_content() -> dict[str, object]:
    """Build the schema-valid response returned by the provider double."""
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


class FakeOpenAI:
    """Capture a Responses parse call while returning schema-valid structured output."""

    calls: list[dict[str, object]] = []

    def __init__(self, **kwargs: object) -> None:
        self.init_kwargs = kwargs
        self.responses = self

    def parse(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append({"init": self.init_kwargs, "request": kwargs})
        return SimpleNamespace(
            output_parsed=StructuredProjectSummary.model_validate(structured_content())
        )


class RateLimitedOpenAI:
    """Provider double that returns a retryable OpenAI rate-limit error."""

    def __init__(self, **kwargs: object) -> None:
        self.responses = self

    def parse(self, **kwargs: object) -> SimpleNamespace:
        response = Response(
            429,
            headers={"retry-after": "30"},
            request=Request("POST", "https://api.openai.com/v1/responses"),
        )
        raise RateLimitError("Rate limit reached.", response=response, body={})


@pytest.mark.asyncio
async def test_openai_summary_agent_uses_structured_responses_contract(monkeypatch) -> None:
    """The adapter sends bounded evidence through GPT-5 structured output with storage disabled."""
    FakeOpenAI.calls.clear()
    monkeypatch.setattr(agent_module, "OpenAI", FakeOpenAI)
    settings = Settings(
        database_url="sqlite+aiosqlite://",
        openai_api_key="test-only-key",
        openai_project_summary_model="gpt-5",
    )
    context = ProjectSummaryContext(
        repository_id=uuid4(),
        repository_version_id=uuid4(),
        repository_name="Demo",
        source_type="zip",
        remote_url=None,
        analysis_results={
            "statistics": {"total_files": 1},
            "environment_files": [".env.example"],
            "symbols": {"classes": [], "functions": []},
        },
    )

    payload = await OpenAIProjectSummaryAgent(settings).generate(context)

    assert payload.model == "gpt-5"
    assert payload.content["overview"]["summary"] == "Grounded summary."
    assert len(FakeOpenAI.calls) == 1
    request = FakeOpenAI.calls[0]["request"]
    assert request["model"] == "gpt-5"
    assert request["text_format"] is StructuredProjectSummary
    assert request["store"] is False
    assert "<repository_evidence>" in request["input"][1]["content"]


@pytest.mark.asyncio
async def test_openai_summary_agent_exposes_rate_limit_retry_guidance(monkeypatch) -> None:
    """OpenAI rate limits become a safe, actionable domain error."""
    monkeypatch.setattr(agent_module, "OpenAI", RateLimitedOpenAI)
    settings = Settings(
        database_url="sqlite+aiosqlite://",
        openai_api_key="test-only-key",
        openai_project_summary_model="gpt-5",
    )
    context = ProjectSummaryContext(
        repository_id=uuid4(),
        repository_version_id=uuid4(),
        repository_name="Demo",
        source_type="zip",
        remote_url=None,
        analysis_results={},
    )

    with pytest.raises(ProjectSummaryRateLimitedError) as error:
        await OpenAIProjectSummaryAgent(settings).generate(context)

    assert error.value.retry_after_seconds == 30
    assert "Wait about 30 seconds" in str(error.value)
