"""Safe errors raised by documentation generation use cases."""


class DocumentationNotFound(Exception):
    """No documentation bundle exists for the latest stored repository version."""


class DocumentationConfigurationError(Exception):
    """The selected documentation provider is not ready to receive a request."""


class DocumentationGenerationError(Exception):
    """The configured provider could not produce a valid documentation bundle."""
