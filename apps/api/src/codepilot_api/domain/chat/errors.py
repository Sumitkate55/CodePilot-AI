"""Repository-chat domain errors safe to map at the HTTP boundary."""


class RepositoryChatNotIndexed(Exception):
    """The current repository version has no ready vector index."""


class RepositoryChatConfigurationError(Exception):
    """A required embedding, chat, or vector-store integration is unavailable."""


class RepositoryChatIndexingError(Exception):
    """The repository source could not be turned into a usable vector index."""


class RepositoryChatGenerationError(Exception):
    """The provider could not create a grounded response from retrieved evidence."""
