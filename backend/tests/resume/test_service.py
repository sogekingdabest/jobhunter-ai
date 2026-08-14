"""Tailored resume application service tests."""

import json
from dataclasses import replace
from datetime import timedelta
from typing import cast
from uuid import UUID, uuid4

import pytest

from jobhunter.ai.application.structured_generation import StructuredGenerationService
from jobhunter.ai.domain.types import (
    FinishReason,
    JSONObject,
    StructuredGenerationRequest,
    StructuredGenerationResponse,
)
from jobhunter.candidate.domain.profile import CandidateProfile
from jobhunter.jobs.domain.offers import JobOffer
from jobhunter.matching.domain.assessments import MatchAssessment
from jobhunter.matching.domain.policy import StructuredMatchingPolicy
from jobhunter.resume.application.errors import (
    IncompleteResumeRewriteError,
    ResumeAssessmentMismatchError,
    ResumeCandidateNotFoundError,
    ResumeJobOfferNotFoundError,
    ResumeLLMNotConfiguredError,
    ResumeMatchAssessmentNotFoundError,
    StaleResumeAssessmentError,
    TailoredResumeAlreadyReviewedError,
    TailoredResumeNotFoundError,
    TailoredResumeReviewConflictError,
)
from jobhunter.resume.application.service import TailoredResumeService
from jobhunter.resume.domain.grounding import UngroundedResumeOutputError
from jobhunter.resume.domain.models import GenerationMethod, ResumeStatus, TailoredResume
from jobhunter.resume.ports.repository import TailoredResumeRepositoryConflictError
from tests.candidate.factories import make_profile
from tests.jobs.factories import make_offer
from tests.matching.test_service import (
    AssessmentRepositoryStub,
    CandidateRepositoryStub,
    JobRepositoryStub,
)
from tests.resume.factories import NOW


class ResumeRepositoryStub:
    def __init__(self, *, conflict: bool = False) -> None:
        self.items: dict[UUID, TailoredResume] = {}
        self.conflict = conflict

    async def add(self, resume: TailoredResume) -> TailoredResume:
        self.items[resume.id] = resume
        return resume

    async def get(self, resume_id: UUID) -> TailoredResume | None:
        return self.items.get(resume_id)

    async def replace(self, resume: TailoredResume) -> TailoredResume | None:
        if self.conflict:
            raise TailoredResumeRepositoryConflictError
        if resume.id not in self.items:
            return None
        self.items[resume.id] = resume
        return resume


class GenerationStub:
    def __init__(
        self,
        *,
        finish_reason: FinishReason = FinishReason.COMPLETE,
        added_term: str | None = None,
    ) -> None:
        self.finish_reason = finish_reason
        self.added_term = added_term
        self.requests: list[StructuredGenerationRequest] = []

    async def generate(self, request: StructuredGenerationRequest) -> StructuredGenerationResponse:
        self.requests.append(request)
        facts = json.loads(request.inputs[0].content)
        rewrites = [
            {
                "selection_id": item["selection_id"],
                "text": item["source_text"] + (f" {self.added_term}" if self.added_term else ""),
            }
            for item in facts
        ]
        output = cast(JSONObject, {"contract_version": "1.0", "rewrites": rewrites})
        return StructuredGenerationResponse(
            request_id=request.id,
            provider="fake",
            model="fixture",
            output=output,
            finish_reason=self.finish_reason,
        )


def context() -> tuple[CandidateProfile, JobOffer, MatchAssessment, AssessmentRepositoryStub]:
    candidate = make_profile()
    offer = make_offer()
    assessment = StructuredMatchingPolicy().assess(candidate, offer, assessed_at=NOW)
    assessments = AssessmentRepositoryStub()
    assessments.assessments[assessment.id] = assessment
    return candidate, offer, assessment, assessments


def service(
    candidate: CandidateProfile | None,
    offer: JobOffer | None,
    assessments: AssessmentRepositoryStub,
    resumes: ResumeRepositoryStub | None = None,
    generation: GenerationStub | None = None,
) -> TailoredResumeService:
    return TailoredResumeService(
        CandidateRepositoryStub(candidate),
        JobRepositoryStub(offer),
        assessments,
        resumes or ResumeRepositoryStub(),
        cast(StructuredGenerationService, generation) if generation else None,
        clock=lambda: NOW,
    )


@pytest.mark.asyncio
async def test_service_creates_extractively_grounded_resume() -> None:
    candidate, offer, assessment, assessments = context()
    resumes = ResumeRepositoryStub()
    tailored = service(candidate, offer, assessments, resumes)

    created = await tailored.create(candidate.id, offer.id, assessment.id)

    assert created.status is ResumeStatus.NEEDS_REVIEW
    assert created.provider is None
    assert all(item.method is GenerationMethod.EXTRACTIVE for item in created.fragments)
    assert all(item.generated_text == item.sources[0].source_text for item in created.fragments)
    assert await tailored.get(created.id) == created


@pytest.mark.asyncio
async def test_service_rewrites_professional_facts_without_sending_identity() -> None:
    candidate, offer, assessment, assessments = context()
    generation = GenerationStub()
    tailored = service(candidate, offer, assessments, generation=generation)

    created = await tailored.create(candidate.id, offer.id, assessment.id, use_llm=True)

    assert created.provider == "fake"
    assert created.model == "fixture"
    assert created.fragments[0].method is GenerationMethod.EXTRACTIVE
    assert all(item.method is GenerationMethod.LLM_REPHRASED for item in created.fragments[1:])
    request = generation.requests[0]
    assert candidate.full_name not in request.inputs[0].content
    assert request.inputs[1].trust.value == "untrusted_external"


@pytest.mark.asyncio
async def test_service_keeps_header_extractive_when_no_professional_facts_exist() -> None:
    candidate, offer, _, _ = context()
    candidate = replace(
        candidate,
        summary=None,
        work_experiences=(),
        education=(),
        projects=(),
        competencies=(),
        languages=(),
    )
    assessment = StructuredMatchingPolicy().assess(candidate, offer, assessed_at=NOW)
    assessments = AssessmentRepositoryStub()
    assessments.assessments[assessment.id] = assessment
    generation = GenerationStub()

    created = await service(candidate, offer, assessments, generation=generation).create(
        candidate.id, offer.id, assessment.id, use_llm=True
    )

    assert len(created.fragments) == 1
    assert created.provider is None
    assert generation.requests == []


@pytest.mark.asyncio
async def test_service_rejects_unsupported_llm_claim() -> None:
    candidate, offer, assessment, assessments = context()
    tailored = service(
        candidate, offer, assessments, generation=GenerationStub(added_term="Kubernetes")
    )

    with pytest.raises(UngroundedResumeOutputError, match="unsupported_resume_claim"):
        await tailored.create(candidate.id, offer.id, assessment.id, use_llm=True)


@pytest.mark.asyncio
async def test_service_rejects_incomplete_llm_output() -> None:
    candidate, offer, assessment, assessments = context()
    tailored = service(
        candidate,
        offer,
        assessments,
        generation=GenerationStub(finish_reason=FinishReason.LENGTH),
    )

    with pytest.raises(IncompleteResumeRewriteError):
        await tailored.create(candidate.id, offer.id, assessment.id, use_llm=True)


@pytest.mark.asyncio
async def test_service_requires_configured_llm() -> None:
    candidate, offer, assessment, assessments = context()
    with pytest.raises(ResumeLLMNotConfiguredError):
        await service(candidate, offer, assessments).create(
            candidate.id, offer.id, assessment.id, use_llm=True
        )


@pytest.mark.asyncio
async def test_service_reports_missing_inputs() -> None:
    candidate, offer, assessment, assessments = context()
    with pytest.raises(ResumeCandidateNotFoundError):
        await service(None, offer, assessments).create(uuid4(), offer.id, assessment.id)
    with pytest.raises(ResumeJobOfferNotFoundError):
        await service(candidate, None, assessments).create(candidate.id, uuid4(), assessment.id)
    with pytest.raises(ResumeMatchAssessmentNotFoundError):
        await service(candidate, offer, AssessmentRepositoryStub()).create(
            candidate.id, offer.id, uuid4()
        )


@pytest.mark.asyncio
async def test_service_rejects_mismatched_and_stale_assessments() -> None:
    candidate, offer, assessment, assessments = context()
    mismatched = replace(assessment, candidate_profile_id=uuid4())
    assessments.assessments[assessment.id] = mismatched
    with pytest.raises(ResumeAssessmentMismatchError):
        await service(candidate, offer, assessments).create(candidate.id, offer.id, assessment.id)

    stale = replace(assessment, candidate_updated_at=assessment.candidate_updated_at - timedelta(1))
    assessments.assessments[assessment.id] = stale
    with pytest.raises(StaleResumeAssessmentError):
        await service(candidate, offer, assessments).create(candidate.id, offer.id, assessment.id)


@pytest.mark.asyncio
async def test_service_reviews_resume_and_translates_conflict() -> None:
    candidate, offer, assessment, assessments = context()
    resumes = ResumeRepositoryStub()
    tailored = service(candidate, offer, assessments, resumes)
    created = await tailored.create(candidate.id, offer.id, assessment.id)

    approved = await tailored.review(created.id, ResumeStatus.APPROVED)

    assert approved.status is ResumeStatus.APPROVED
    with pytest.raises(TailoredResumeAlreadyReviewedError):
        await tailored.review(created.id, ResumeStatus.REJECTED)

    conflicting = ResumeRepositoryStub(conflict=True)
    conflicting.items[created.id] = created
    with pytest.raises(TailoredResumeReviewConflictError):
        await service(candidate, offer, assessments, conflicting).review(
            created.id, ResumeStatus.REJECTED
        )


@pytest.mark.asyncio
async def test_service_reports_missing_resume() -> None:
    candidate, offer, _, assessments = context()
    with pytest.raises(TailoredResumeNotFoundError):
        await service(candidate, offer, assessments).get(uuid4())
