"""Orchestrate matching without coupling policy to persistence."""

from datetime import datetime
from uuid import UUID

from jobhunter.candidate.ports.repository import CandidateProfileRepository
from jobhunter.jobs.ports.repository import JobOfferRepository
from jobhunter.matching.application.errors import (
    MatchAssessmentNotFoundError,
    MatchCandidateNotFoundError,
    MatchJobOfferNotFoundError,
)
from jobhunter.matching.domain.assessments import MatchAssessment
from jobhunter.matching.domain.policy import StructuredMatchingPolicy
from jobhunter.matching.ports.repository import MatchAssessmentRepository


class StructuredMatchingService:
    """Load trusted aggregates, apply one policy, and persist its snapshot."""

    def __init__(
        self,
        candidate_repository: CandidateProfileRepository,
        job_repository: JobOfferRepository,
        assessment_repository: MatchAssessmentRepository,
        policy: StructuredMatchingPolicy | None = None,
    ) -> None:
        self._candidates = candidate_repository
        self._jobs = job_repository
        self._assessments = assessment_repository
        self._policy = policy or StructuredMatchingPolicy()

    async def assess(
        self,
        candidate_profile_id: UUID,
        job_offer_id: UUID,
        *,
        assessed_at: datetime | None = None,
    ) -> MatchAssessment:
        candidate = await self._candidates.get(candidate_profile_id)
        if candidate is None:
            raise MatchCandidateNotFoundError
        offer = await self._jobs.get(job_offer_id)
        if offer is None:
            raise MatchJobOfferNotFoundError
        assessment = self._policy.assess(candidate, offer, assessed_at=assessed_at)
        return await self._assessments.add(assessment)

    async def get(self, assessment_id: UUID) -> MatchAssessment:
        assessment = await self._assessments.get(assessment_id)
        if assessment is None:
            raise MatchAssessmentNotFoundError
        return assessment
