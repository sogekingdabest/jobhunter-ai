"""Direct route tests for tailored resume error translation and contracts."""

from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.resume.api.routes import (
    create_tailored_resume,
    get_service,
    get_tailored_resume,
    review_tailored_resume,
)
from jobhunter.resume.api.schemas import ResumeReviewInput, TailoredResumeInput
from jobhunter.resume.application.errors import (
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
from jobhunter.resume.domain.models import ResumeStatus, TailoredResume
from tests.resume.factories import make_resume


class RouteServiceStub:
    def __init__(self, error: Exception | None = None) -> None:
        self.resume = make_resume()
        self.error = error

    async def create(
        self,
        candidate_profile_id: UUID,
        job_offer_id: UUID,
        match_assessment_id: UUID,
        *,
        use_llm: bool = False,
    ) -> TailoredResume:
        del candidate_profile_id, job_offer_id, match_assessment_id, use_llm
        if self.error:
            raise self.error
        return self.resume

    async def get(self, resume_id: UUID) -> TailoredResume:
        del resume_id
        if self.error:
            raise self.error
        return self.resume

    async def review(self, resume_id: UUID, decision: ResumeStatus) -> TailoredResume:
        del resume_id
        if self.error:
            raise self.error
        return self.resume.review(decision, reviewed_at=self.resume.created_at)


def as_service(stub: RouteServiceStub) -> TailoredResumeService:
    return cast(TailoredResumeService, stub)


@pytest.mark.asyncio
async def test_routes_create_get_and_review_resume() -> None:
    stub = RouteServiceStub()
    payload = TailoredResumeInput(
        candidate_profile_id=stub.resume.candidate_profile_id,
        job_offer_id=stub.resume.job_offer_id,
        match_assessment_id=stub.resume.match_assessment_id,
    )

    created = await create_tailored_resume(payload, as_service(stub))
    fetched = await get_tailored_resume(created.id, as_service(stub))
    reviewed = await review_tailored_resume(
        created.id,
        ResumeReviewInput(decision=ResumeStatus.APPROVED),
        as_service(stub),
    )

    assert fetched == created
    assert reviewed.status is ResumeStatus.APPROVED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "code", "detail"),
    [
        (ResumeCandidateNotFoundError(), status.HTTP_404_NOT_FOUND, "candidate_profile_not_found"),
        (ResumeJobOfferNotFoundError(), status.HTTP_404_NOT_FOUND, "job_offer_not_found"),
        (
            ResumeMatchAssessmentNotFoundError(),
            status.HTTP_404_NOT_FOUND,
            "match_assessment_not_found",
        ),
        (ResumeAssessmentMismatchError(), status.HTTP_409_CONFLICT, "match_assessment_mismatch"),
        (StaleResumeAssessmentError(), status.HTTP_409_CONFLICT, "match_assessment_stale"),
        (
            ResumeLLMNotConfiguredError(),
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "resume_llm_not_configured",
        ),
    ],
)
async def test_create_route_translates_errors(error: Exception, code: int, detail: str) -> None:
    resume = make_resume()
    payload = TailoredResumeInput(
        candidate_profile_id=resume.candidate_profile_id,
        job_offer_id=resume.job_offer_id,
        match_assessment_id=resume.match_assessment_id,
    )

    with pytest.raises(HTTPException) as captured:
        await create_tailored_resume(payload, as_service(RouteServiceStub(error)))

    assert captured.value.status_code == code
    assert captured.value.detail == detail


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("operation", "error", "detail"),
    [
        ("get", TailoredResumeNotFoundError(), "tailored_resume_not_found"),
        ("review", TailoredResumeNotFoundError(), "tailored_resume_not_found"),
        (
            "review",
            TailoredResumeAlreadyReviewedError(),
            "tailored_resume_already_reviewed",
        ),
        ("review", TailoredResumeReviewConflictError(), "tailored_resume_changed"),
    ],
)
async def test_read_and_review_routes_translate_errors(
    operation: str, error: Exception, detail: str
) -> None:
    stub = as_service(RouteServiceStub(error))
    call = (
        get_tailored_resume(uuid4(), stub)
        if operation == "get"
        else review_tailored_resume(
            uuid4(), ResumeReviewInput(decision=ResumeStatus.REJECTED), stub
        )
    )
    with pytest.raises(HTTPException) as captured:
        await call

    assert captured.value.status_code in {status.HTTP_404_NOT_FOUND, status.HTTP_409_CONFLICT}
    assert captured.value.detail == detail


def test_route_contracts_are_strict_and_dependency_wires_adapters() -> None:
    with pytest.raises(ValidationError):
        TailoredResumeInput.model_validate(
            {
                "candidate_profile_id": str(uuid4()),
                "job_offer_id": str(uuid4()),
                "match_assessment_id": str(uuid4()),
                "extra": True,
            }
        )
    with pytest.raises(ValidationError):
        ResumeReviewInput.model_validate({"decision": "needs_review"})

    assert isinstance(get_service(cast(AsyncSession, object())), TailoredResumeService)
