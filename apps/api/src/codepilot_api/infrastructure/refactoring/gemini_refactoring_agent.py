"""Gemini adapter for source-grounded refactoring proposals."""

from __future__ import annotations

import json

from codepilot_api.config.settings import Settings
from codepilot_api.domain.refactoring.entities import RefactoringContext, RefactorProposalPayload
from codepilot_api.domain.refactoring.errors import (
    RefactoringConfigurationError,
    RefactoringGenerationError,
)
from codepilot_api.infrastructure.gemini.client import (
    GeminiClient,
    GeminiResponseError,
    GeminiUnavailableError,
)
from codepilot_api.infrastructure.refactoring.openai_refactoring_agent import (
    SYSTEM_INSTRUCTIONS,
    OpenAIRefactoringAgent,
    StructuredRefactorProposal,
)


class GeminiRefactoringAgent:
    """Generate one source-grounded refactor with Gemini structured output."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.gemini_api_key
        self._model = settings.gemini_generation_model
        self._timeout_seconds = settings.gemini_timeout_seconds

    async def propose(self, context: RefactoringContext) -> RefactorProposalPayload:
        """Produce a replacement source proposal limited to supplied evidence."""
        if self._api_key is None or not self._api_key.get_secret_value():
            raise RefactoringConfigurationError(
                "Refactoring proposals require GEMINI_API_KEY to be configured on the API server."
            )
        client = GeminiClient(self._api_key.get_secret_value(), self._timeout_seconds)
        try:
            result = await client.chat_json(
                self._model,
                SYSTEM_INSTRUCTIONS,
                "Generate one refactoring proposal using only this JSON evidence.\n"
                "<refactoring_evidence>"
                f"{json.dumps(OpenAIRefactoringAgent._evidence(context), ensure_ascii=True)}"
                "</refactoring_evidence>",
                StructuredRefactorProposal,
            )
        except GeminiUnavailableError as error:
            raise RefactoringConfigurationError(str(error)) from error
        except GeminiResponseError as error:
            raise RefactoringGenerationError(str(error)) from error
        return OpenAIRefactoringAgent._payload(result, f"gemini/{self._model}")
