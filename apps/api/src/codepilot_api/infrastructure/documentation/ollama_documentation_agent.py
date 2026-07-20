"""Local Ollama adapter for source-grounded documentation generation."""

from __future__ import annotations

import json

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
from codepilot_api.infrastructure.ollama.client import (
    OllamaClient,
    OllamaResponseError,
    OllamaUnavailableError,
)


class OllamaDocumentationAgent:
    """Generate validated documentation bundles with the configured local model."""

    def __init__(self, settings: Settings) -> None:
        self._model = settings.ollama_chat_model
        self._client = OllamaClient(settings.ollama_base_url, settings.ollama_timeout_seconds)

    async def generate(self, context: DocumentationContext) -> DocumentationPayload:
        """Keep source intelligence local while asking Ollama for structured Markdown."""
        evidence = {
            "repository": {
                "name": context.repository_name,
                "source_type": context.source_type,
                "has_remote_url": context.remote_url is not None,
            },
            "repository_intelligence": OpenAIDocumentationAgent.compact_evidence(
                context.analysis_results
            ),
        }
        try:
            result = await self._client.chat_json(
                self._model,
                SYSTEM_INSTRUCTIONS,
                "Generate every requested Markdown document using only this JSON evidence.\n"
                "<repository_evidence>"
                f"{json.dumps(evidence, ensure_ascii=True)}"
                "</repository_evidence>",
                StructuredDocumentation,
                num_predict=8_192,
            )
        except OllamaUnavailableError as error:
            raise DocumentationConfigurationError(str(error)) from error
        except OllamaResponseError as error:
            raise DocumentationGenerationError(str(error)) from error
        return OpenAIDocumentationAgent.payload(result, f"ollama/{self._model}")
