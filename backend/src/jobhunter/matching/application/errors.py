"""Application errors exposed independently of adapters."""


class MatchCandidateNotFoundError(LookupError):
    """The requested candidate profile does not exist."""


class MatchJobOfferNotFoundError(LookupError):
    """The requested normalized job offer does not exist."""


class MatchAssessmentNotFoundError(LookupError):
    """The requested assessment does not exist."""
