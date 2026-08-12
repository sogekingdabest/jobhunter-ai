"""Application-level candidate profile errors."""


class CandidateProfileNotFoundError(LookupError):
    """Raised when the requested candidate profile does not exist."""


class CandidateProfileAlreadyExistsError(ValueError):
    """Raised when creating an aggregate with an existing identity."""
