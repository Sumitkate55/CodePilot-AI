"""Ollama adapter for source-grounded project summaries without API billing."""

from __future__ import annotations

from codepilot_api.config.settings import Settings
from codepilot_api.domain.summaries.entities import ProjectSummaryContext, ProjectSummaryPayload
from codepilot_api.domain.summaries.errors import (
    ProjectSummaryConfigurationError,
    ProjectSummaryGenerationError,
)
from codepilot_api.infrastructure.ollama.client import (
    OllamaClient,
    OllamaResponseError,
    OllamaUnavailableError,
)
from codepilot_api.infrastructure.summaries.openai_project_summary_agent import (
    PROMPT_VERSION,
    SYSTEM_INSTRUCTIONS,
    OpenAIProjectSummaryAgent,
    StructuredProjectSummary,
)


class OllamaProjectSummaryAgent:
    """Generate the established structured summary with a locally running Ollama model."""

    def __init__(self, settings: Settings) -> None:
        self._model = settings.ollama_chat_model
        self._client = OllamaClient(settings.ollama_base_url, settings.ollama_timeout_seconds)

    async def generate(self, context: ProjectSummaryContext) -> ProjectSummaryPayload:
        """Generate a schema-validated summary from bounded repository intelligence."""
        try:
            summary = await self._client.chat_json(
                self._model,
                SYSTEM_INSTRUCTIONS,
                OpenAIProjectSummaryAgent._user_prompt(context),
                StructuredProjectSummary,
            )
        except OllamaUnavailableError as error:
            raise ProjectSummaryConfigurationError(str(error)) from error
        except OllamaResponseError as error:
            raise ProjectSummaryGenerationError(str(error)) from error
        return ProjectSummaryPayload(
            model=f"ollama/{self._model}",
            prompt_version=PROMPT_VERSION,
            content=summary.model_dump(mode="json"),
        )
