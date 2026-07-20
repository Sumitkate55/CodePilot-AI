"""Gemini adapter for source-grounded code explanations."""

from __future__ import annotations

import json

from codepilot_api.config.settings import Settings
from codepilot_api.domain.explanations.entities import (
    CodeExplanationContext,
    CodeExplanationPayload,
)
from codepilot_api.domain.explanations.errors import (
    CodeExplanationConfigurationError,
    CodeExplanationGenerationError,
)
from codepilot_api.infrastructure.explanations.openai_code_explanation_agent import (
    SYSTEM_INSTRUCTIONS,
    StructuredCodeExplanation,
)
from codepilot_api.infrastructure.gemini.client import (
    GeminiClient,
    GeminiResponseError,
    GeminiUnavailableError,
)


class GeminiCodeExplanationAgent:
    """Generate a schema-validated function explanation with Gemini."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.gemini_api_key
        self._model = settings.gemini_generation_model
        self._timeout_seconds = settings.gemini_timeout_seconds

    async def explain(self, context: CodeExplanationContext) -> CodeExplanationPayload:
        """Explain only the selected source evidence."""
        if self._api_key is None or not self._api_key.get_secret_value():
            raise CodeExplanationConfigurationError(
                "Code explanations require GEMINI_API_KEY to be configured on the API server."
            )
        evidence = {
            "function": {
                "name": context.function.name,
                "path": context.function.path,
                "start_line": context.function.line,
                "end_line": context.end_line,
                "language": context.function.language,
            },
            "source": context.source,
        }
        client = GeminiClient(self._api_key.get_secret_value(), self._timeout_seconds)
        try:
            result = await client.chat_json(
                self._model,
                SYSTEM_INSTRUCTIONS,
                "Explain this selected function using only the JSON evidence below.\n"
                f"<function_evidence>{json.dumps(evidence, ensure_ascii=True)}</function_evidence>",
                StructuredCodeExplanation,
            )
        except GeminiUnavailableError as error:
            raise CodeExplanationConfigurationError(str(error)) from error
        except GeminiResponseError as error:
            raise CodeExplanationGenerationError(str(error)) from error
        return CodeExplanationPayload(
            model=f"gemini/{self._model}", content=result.model_dump(mode="json")
        )
