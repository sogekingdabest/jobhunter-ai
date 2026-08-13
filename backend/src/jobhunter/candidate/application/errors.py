"""Application-level candidate profile errors."""


class CandidateProfileNotFoundError(LookupError):
    """Raised when the requested candidate profile does not exist."""


class CandidateProfileAlreadyExistsError(ValueError):
    """Raised when creating an aggregate with an existing identity."""


class CandidateFactExtractionNotFoundError(LookupError):
    """Raised when a requested extraction does not exist."""


class CandidateFactProposalNotFoundError(LookupError):
    """Raised when a proposal is not owned by the requested extraction."""


class CandidateFactAlreadyReviewedError(ValueError):
    """Raised when a review decision would overwrite the audit trail."""


class CandidateFactReviewConflictError(ValueError):
    """Raised when concurrent review changed the extraction first."""


class UngroundedCandidateFactError(ValueError):
    """Raised when model evidence is not an exact parsed-document span."""


class IncompleteCandidateFactExtractionError(ValueError):
    """Raised when a provider stops before completing structured extraction."""
