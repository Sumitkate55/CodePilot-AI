"""Errors emitted by source-grounded unit-test generation."""


class TestGenerationNotFound(Exception):
    """No generated test file exists for the selected source function."""


class TestGenerationTargetNotFound(Exception):
    """The requested source location is not a detected function in the latest analysis."""


class TestGenerationUnsupported(Exception):
    """The selected function language has no supported test framework."""


class TestGenerationConfigurationError(Exception):
    """The selected AI provider is not configured for test generation."""


class TestGenerationError(Exception):
    """The AI provider could not generate a valid unit-test artifact."""
