"""Local Ollama adapter for grounded code explanations."""

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
from codepilot_api.infrastructure.ollama.client import (
    OllamaClient,
    OllamaResponseError,
    OllamaUnavailableError,
)


class OllamaCodeExplanationAgent:
    """Generate a validated explanation with a local Ollama code model."""

    def __init__(self, settings: Settings) -> None:
        self._model = settings.ollama_chat_model
        self._client = OllamaClient(settings.ollama_base_url, settings.ollama_timeout_seconds)

    async def explain(self, context: CodeExplanationContext) -> CodeExplanationPayload:
        """Explain selected source without sending it to a cloud provider."""
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
        try:
            result = await self._client.chat_json(
                self._model,
                SYSTEM_INSTRUCTIONS,
                "Explain this selected function using only the JSON evidence below.\n"
                f"<function_evidence>{json.dumps(evidence, ensure_ascii=True)}</function_evidence>",
                StructuredCodeExplanation,
            )
        except OllamaUnavailableError as error:
            raise CodeExplanationConfigurationError(str(error)) from error
        except OllamaResponseError as error:
            raise CodeExplanationGenerationError(str(error)) from error
        return CodeExplanationPayload(
            model=f"ollama/{self._model}", content=result.model_dump(mode="json")
        )
