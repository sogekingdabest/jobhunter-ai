"""Safe application errors for job offer workflows."""


class DuplicateJobOfferError(ValueError):
    """Raised when canonical source content was already imported."""


class JobOfferNotFoundError(LookupError):
    """Raised when an offer identity is unknown."""


class UngroundedJobNormalizationError(ValueError):
    """Raised when normalized output lacks exact source support."""


class IncompleteJobNormalizationError(ValueError):
    """Raised when inference ended before a complete structured response."""


class UnsafeJobUrlError(ValueError):
    """Raised when a URL could reach a non-public or unsupported destination."""


class JobUrlFetchError(RuntimeError):
    """Raised when a permitted remote resource cannot be retrieved."""


class InvalidJobUrlContentError(ValueError):
    """Raised when a response is too large, unsupported, or has no useful text."""


class JobUrlContentChangedError(ValueError):
    """Raised when reviewed URL content changed before import."""
