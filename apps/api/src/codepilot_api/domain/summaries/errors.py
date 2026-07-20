"""Project-summary domain errors."""


class ProjectSummaryNotFound(Exception):
    """The latest repository version does not yet have a generated summary."""


class ProjectSummaryConfigurationError(Exception):
    """The AI provider credentials or required configuration are unavailable."""


class ProjectSummaryGenerationError(Exception):
    """The configured AI provider could not produce a valid project summary."""


class ProjectSummaryRateLimitedError(ProjectSummaryGenerationError):
    """The AI provider temporarily rejected a summary request because of a rate limit."""

    def __init__(self, retry_after_seconds: int | None = None) -> None:
        self.retry_after_seconds = retry_after_seconds
        wait_guidance = (
            f" Wait about {retry_after_seconds} seconds before retrying."
            if retry_after_seconds is not None
            else " Wait a minute before retrying."
        )
        super().__init__(
            "OpenAI has temporarily rate-limited project summary generation."
            f"{wait_guidance} If this continues, review your OpenAI API billing and usage limits."
        )
