"""Application service tests for structured matching."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from jobhunter.candidate.domain.profile import CandidateProfile
from jobhunter.documents.domain.entities import EvidenceSource, EvidenceSpan
from jobhunter.jobs.domain.offers import JobOffer
from jobhunter.matching.application.errors import (
    MatchAssessmentNotFoundError,
    MatchCandidateNotFoundError,
    MatchJobOfferNotFoundError,
)
from jobhunter.matching.application.service import StructuredMatchingService
from jobhunter.matching.domain.assessments import MatchAssessment
from tests.candidate.factories import make_profile
from tests.jobs.factories import make_offer

NOW = datetime(2026, 8, 13, 14, tzinfo=UTC)


class CandidateRepositoryStub:
    def __init__(self, profile: CandidateProfile | None) -> None:
        self.profile = profile

    async def add(self, profile: CandidateProfile) -> CandidateProfile:
        self.profile = profile
        return profile

    async def get(self, profile_id: UUID) -> CandidateProfile | None:
        return self.profile if self.profile and self.profile.id == profile_id else None

    async def replace(self, profile: CandidateProfile) -> CandidateProfile | None:
        self.profile = profile
        return profile

    async def delete(self, profile_id: UUID) -> bool:
        del profile_id
        self.profile = None
        return True


class JobRepositoryStub:
    def __init__(self, offer: JobOffer | None) -> None:
        self.offer = offer

    async def add(
        self,
        offer: JobOffer,
        evidence_source: EvidenceSource,
        evidence_spans: tuple[EvidenceSpan, ...],
    ) -> JobOffer:
        del evidence_source, evidence_spans
        self.offer = offer
        return offer

    async def get(self, offer_id: UUID) -> JobOffer | None:
        return self.offer if self.offer and self.offer.id == offer_id else None

    async def get_by_fingerprint(self, fingerprint: str) -> JobOffer | None:
        return self.offer if self.offer and self.offer.content_fingerprint == fingerprint else None


class AssessmentRepositoryStub:
    def __init__(self) -> None:
        self.assessments: dict[UUID, MatchAssessment] = {}

    async def add(self, assessment: MatchAssessment) -> MatchAssessment:
        self.assessments[assessment.id] = assessment
        return assessment

    async def get(self, assessment_id: UUID) -> MatchAssessment | None:
        return self.assessments.get(assessment_id)


def service(
    candidate: CandidateProfile | None, offer: JobOffer | None
) -> StructuredMatchingService:
    return StructuredMatchingService(
        CandidateRepositoryStub(candidate), JobRepositoryStub(offer), AssessmentRepositoryStub()
    )


@pytest.mark.asyncio
async def test_service_creates_and_gets_persisted_assessment() -> None:
    candidate, offer = make_profile(), make_offer()
    matching = service(candidate, offer)

    created = await matching.assess(candidate.id, offer.id, assessed_at=NOW)

    assert created.assessed_at == NOW
    assert await matching.get(created.id) == created


@pytest.mark.asyncio
async def test_service_reports_missing_candidate_before_loading_offer() -> None:
    matching = service(None, make_offer())

    with pytest.raises(MatchCandidateNotFoundError):
        await matching.assess(uuid4(), uuid4())


@pytest.mark.asyncio
async def test_service_reports_missing_offer() -> None:
    candidate = make_profile()
    matching = service(candidate, None)

    with pytest.raises(MatchJobOfferNotFoundError):
        await matching.assess(candidate.id, uuid4())


@pytest.mark.asyncio
async def test_service_reports_missing_assessment() -> None:
    with pytest.raises(MatchAssessmentNotFoundError):
        await service(None, None).get(uuid4())
