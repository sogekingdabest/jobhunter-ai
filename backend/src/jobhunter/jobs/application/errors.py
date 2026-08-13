"""Safe application errors for job offer workflows."""


class DuplicateJobOfferError(ValueError):
    """Raised when canonical source content was already imported."""


class JobOfferNotFoundError(LookupError):
    """Raised when an offer identity is unknown."""


class UngroundedJobNormalizationError(ValueError):
    """Raised when normalized output lacks exact source support."""


class IncompleteJobNormalizationError(ValueError):
    """Raised when inference ended before a complete structured response."""
