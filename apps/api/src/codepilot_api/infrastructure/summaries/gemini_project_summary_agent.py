"""Gemini adapter for source-grounded project summaries."""

from __future__ import annotations

from codepilot_api.config.settings import Settings
from codepilot_api.domain.summaries.entities import ProjectSummaryContext, ProjectSummaryPayload
from codepilot_api.domain.summaries.errors import (
    ProjectSummaryConfigurationError,
    ProjectSummaryGenerationError,
)
from codepilot_api.infrastructure.gemini.client import (
    GeminiClient,
    GeminiResponseError,
    GeminiUnavailableError,
)
from codepilot_api.infrastructure.summaries.openai_project_summary_agent import (
    PROMPT_VERSION,
    SYSTEM_INSTRUCTIONS,
    OpenAIProjectSummaryAgent,
    StructuredProjectSummary,
)


class GeminiProjectSummaryAgent:
    """Generate the established structured summary using Gemini on the API server."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.gemini_api_key
        self._model = settings.gemini_generation_model
        self._timeout_seconds = settings.gemini_timeout_seconds

    async def generate(self, context: ProjectSummaryContext) -> ProjectSummaryPayload:
        """Generate a bounded summary from deterministic repository intelligence."""
        if self._api_key is None or not self._api_key.get_secret_value():
            raise ProjectSummaryConfigurationError(
                "Project summaries require GEMINI_API_KEY to be configured on the API server."
            )
        client = GeminiClient(self._api_key.get_secret_value(), self._timeout_seconds)
        try:
            summary = await client.chat_json(
                self._model,
                SYSTEM_INSTRUCTIONS,
                OpenAIProjectSummaryAgent._user_prompt(context),
                StructuredProjectSummary,
            )
        except GeminiUnavailableError as error:
            raise ProjectSummaryConfigurationError(str(error)) from error
        except GeminiResponseError as error:
            raise ProjectSummaryGenerationError(str(error)) from error
        return ProjectSummaryPayload(
            model=f"gemini/{self._model}",
            prompt_version=PROMPT_VERSION,
            content=summary.model_dump(mode="json"),
        )
