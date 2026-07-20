"""Repository code-review domain errors."""


class RepositoryCodeReviewNotFound(Exception):
    """No code review has been created for the latest repository version."""


class RepositoryCodeReviewError(Exception):
    """The stored repository source could not be reviewed safely."""
