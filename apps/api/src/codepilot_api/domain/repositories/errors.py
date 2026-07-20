"""Repository-management domain errors."""


class RepositoryNotFound(Exception):
    """The requested repository does not belong to the current user."""


class RepositoryImportError(Exception):
    """A Git or archive source cannot safely become a repository workspace."""


class InvalidRepositorySource(RepositoryImportError):
    """A source URL or archive violates the repository intake policy."""


class RepositoryAnalysisNotFound(Exception):
    """The repository version has not yet been analyzed."""


class RepositoryAnalysisError(Exception):
    """The stored source cannot be analyzed safely or completely."""
