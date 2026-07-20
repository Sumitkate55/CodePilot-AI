"""Local Ollama adapter for source-grounded refactoring proposals."""

from __future__ import annotations

import json

from codepilot_api.config.settings import Settings
from codepilot_api.domain.refactoring.entities import RefactoringContext, RefactorProposalPayload
from codepilot_api.domain.refactoring.errors import (
    RefactoringConfigurationError,
    RefactoringGenerationError,
)
from codepilot_api.infrastructure.ollama.client import (
    OllamaClient,
    OllamaResponseError,
    OllamaUnavailableError,
)
from codepilot_api.infrastructure.refactoring.openai_refactoring_agent import (
    SYSTEM_INSTRUCTIONS,
    OpenAIRefactoringAgent,
    StructuredRefactorProposal,
)


class OllamaRefactoringAgent:
    """Generate validated refactor proposals with a locally installed code model."""

    def __init__(self, settings: Settings) -> None:
        self._model = settings.ollama_chat_model
        self._client = OllamaClient(settings.ollama_base_url, settings.ollama_timeout_seconds)

    async def propose(self, context: RefactoringContext) -> RefactorProposalPayload:
        """Keep source evidence on the local machine while using Ollama JSON mode."""
        evidence = OpenAIRefactoringAgent._evidence(context)
        try:
            result = await self._client.chat_json(
                self._model,
                SYSTEM_INSTRUCTIONS,
                "Generate one refactoring proposal using only this JSON evidence.\n"
                "<refactoring_evidence>"
                f"{json.dumps(evidence, ensure_ascii=True)}"
                "</refactoring_evidence>",
                StructuredRefactorProposal,
            )
        except OllamaUnavailableError as error:
            raise RefactoringConfigurationError(str(error)) from error
        except OllamaResponseError as error:
            raise RefactoringGenerationError(str(error)) from error
        return OpenAIRefactoringAgent._payload(result, f"ollama/{self._model}")
