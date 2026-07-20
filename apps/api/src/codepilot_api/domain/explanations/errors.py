"""Code-explanation domain errors safe to expose at the HTTP boundary."""


class CodeExplanationNotFound(Exception):
    """The requested path and line do not identify a detected function."""


class CodeExplanationConfigurationError(Exception):
    """The selected AI provider is unavailable or not configured."""


class CodeExplanationGenerationError(Exception):
    """The selected provider could not return a valid explanation."""
