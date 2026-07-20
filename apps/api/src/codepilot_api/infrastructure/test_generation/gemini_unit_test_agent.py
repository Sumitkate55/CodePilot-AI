"""Gemini adapter for source-grounded unit-test generation."""

from __future__ import annotations

import json

from codepilot_api.config.settings import Settings
from codepilot_api.domain.test_generation.entities import (
    GeneratedTestPayload,
    TestGenerationContext,
)
from codepilot_api.domain.test_generation.errors import (
    TestGenerationConfigurationError,
    TestGenerationError,
)
from codepilot_api.infrastructure.gemini.client import (
    GeminiClient,
    GeminiResponseError,
    GeminiUnavailableError,
)
from codepilot_api.infrastructure.test_generation.openai_unit_test_agent import (
    SYSTEM_INSTRUCTIONS,
    OpenAIUnitTestGenerationAgent,
    StructuredGeneratedTest,
)


class GeminiUnitTestGenerationAgent:
    """Generate one validated test file with the configured Gemini model."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.gemini_api_key
        self._model = settings.gemini_generation_model
        self._timeout_seconds = settings.gemini_timeout_seconds

    async def generate(self, context: TestGenerationContext) -> GeneratedTestPayload:
        """Generate all required test scenarios using only selected source evidence."""
        if self._api_key is None or not self._api_key.get_secret_value():
            raise TestGenerationConfigurationError(
                "Generated tests require GEMINI_API_KEY to be configured on the API server."
            )
        client = GeminiClient(self._api_key.get_secret_value(), self._timeout_seconds)
        try:
            result = await client.chat_json(
                self._model,
                SYSTEM_INSTRUCTIONS,
                "Generate a complete unit-test file using only this JSON evidence.\n"
                "<test_generation_evidence>"
                f"{json.dumps(OpenAIUnitTestGenerationAgent.evidence(context), ensure_ascii=True)}"
                "</test_generation_evidence>",
                StructuredGeneratedTest,
                max_output_tokens=8_192,
            )
        except GeminiUnavailableError as error:
            raise TestGenerationConfigurationError(str(error)) from error
        except GeminiResponseError as error:
            raise TestGenerationError(str(error)) from error
        return OpenAIUnitTestGenerationAgent.payload(result, f"gemini/{self._model}")
