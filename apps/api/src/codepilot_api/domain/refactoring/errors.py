"""Errors safe to expose from refactoring-advisor use cases."""


class RefactoringDashboardNotFound(Exception):
    """The repository has no current code review to advise on."""


class RefactoringFindingNotFound(Exception):
    """The requested finding does not belong to the current review."""


class RefactorProposalNotFound(Exception):
    """The requested proposal does not belong to the current source version."""


class RefactoringConfigurationError(Exception):
    """The configured AI provider cannot create a refactor proposal."""


class RefactoringGenerationError(Exception):
    """The AI provider could not return a safe structured proposal."""
