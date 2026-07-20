"""Gemini adapter for source-grounded documentation generation."""

from __future__ import annotations

from codepilot_api.config.settings import Settings
from codepilot_api.domain.documentation.entities import DocumentationContext, DocumentationPayload
from codepilot_api.domain.documentation.errors import (
    DocumentationConfigurationError,
    DocumentationGenerationError,
)
from codepilot_api.infrastructure.documentation.openai_documentation_agent import (
    SYSTEM_INSTRUCTIONS,
    OpenAIDocumentationAgent,
    StructuredDocumentation,
)
from codepilot_api.infrastructure.gemini.client import (
    GeminiClient,
    GeminiResponseError,
    GeminiUnavailableError,
)


class GeminiDocumentationAgent:
    """Generate the saved documentation bundle using Gemini structured output."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.gemini_api_key
        self._model = settings.gemini_generation_model
        self._timeout_seconds = settings.gemini_timeout_seconds

    async def generate(self, context: DocumentationContext) -> DocumentationPayload:
        """Generate every documentation artifact from bounded intelligence evidence."""
        if self._api_key is None or not self._api_key.get_secret_value():
            raise DocumentationConfigurationError(
                "Documentation generation requires GEMINI_API_KEY on the API server."
            )
        client = GeminiClient(self._api_key.get_secret_value(), self._timeout_seconds)
        try:
            result = await client.chat_json(
                self._model,
                SYSTEM_INSTRUCTIONS,
                OpenAIDocumentationAgent.user_prompt(context),
                StructuredDocumentation,
                max_output_tokens=16_384,
            )
        except GeminiUnavailableError as error:
            raise DocumentationConfigurationError(str(error)) from error
        except GeminiResponseError as error:
            raise DocumentationGenerationError(str(error)) from error
        return OpenAIDocumentationAgent.payload(result, f"gemini/{self._model}")
