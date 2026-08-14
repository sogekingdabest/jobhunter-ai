"""Application-level tailored resume errors."""


class ResumeCandidateNotFoundError(LookupError):
    pass


class ResumeJobOfferNotFoundError(LookupError):
    pass


class ResumeMatchAssessmentNotFoundError(LookupError):
    pass


class ResumeAssessmentMismatchError(ValueError):
    pass


class StaleResumeAssessmentError(ValueError):
    pass


class TailoredResumeNotFoundError(LookupError):
    pass


class TailoredResumeAlreadyReviewedError(ValueError):
    pass


class TailoredResumeReviewConflictError(ValueError):
    pass


class IncompleteResumeRewriteError(ValueError):
    pass


class ResumeLLMNotConfiguredError(RuntimeError):
    pass
