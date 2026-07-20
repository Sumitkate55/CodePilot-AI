"""Local Ollama adapter for source-grounded unit-test generation."""

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
from codepilot_api.infrastructure.ollama.client import (
    OllamaClient,
    OllamaResponseError,
    OllamaUnavailableError,
)
from codepilot_api.infrastructure.test_generation.openai_unit_test_agent import (
    SYSTEM_INSTRUCTIONS,
    OpenAIUnitTestGenerationAgent,
    StructuredGeneratedTest,
)


class OllamaUnitTestGenerationAgent:
    """Generate validated test files with the configured local code model."""

    def __init__(self, settings: Settings) -> None:
        self._model = settings.ollama_chat_model
        self._client = OllamaClient(settings.ollama_base_url, settings.ollama_timeout_seconds)

    async def generate(self, context: TestGenerationContext) -> GeneratedTestPayload:
        """Keep test evidence local while asking Ollama for a structured test artifact."""
        evidence = OpenAIUnitTestGenerationAgent.evidence(context)
        try:
            result = await self._client.chat_json(
                self._model,
                SYSTEM_INSTRUCTIONS,
                "Generate a complete unit-test file using only this JSON evidence.\n"
                "<test_generation_evidence>"
                f"{json.dumps(evidence, ensure_ascii=True)}"
                "</test_generation_evidence>",
                StructuredGeneratedTest,
            )
        except OllamaUnavailableError as error:
            raise TestGenerationConfigurationError(str(error)) from error
        except OllamaResponseError as error:
            raise TestGenerationError(str(error)) from error
        return OpenAIUnitTestGenerationAgent.payload(result, f"ollama/{self._model}")
