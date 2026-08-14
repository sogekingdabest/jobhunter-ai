"""REST endpoints for safe tailored resume drafts and review."""

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.candidate.infrastructure.database.repository import (
    SqlAlchemyCandidateProfileRepository,
)
from jobhunter.infrastructure.database.session import Database
from jobhunter.jobs.infrastructure.database.repository import SqlAlchemyJobOfferRepository
from jobhunter.matching.infrastructure.database.repository import (
    SqlAlchemyMatchAssessmentRepository,
)
from jobhunter.resume.api.schemas import (
    ResumeReviewInput,
    TailoredResumeInput,
    TailoredResumeResponse,
)
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
from jobhunter.resume.infrastructure.database.repository import (
    SqlAlchemyTailoredResumeRepository,
)

router = APIRouter(prefix="/tailored-resumes", tags=["tailored resumes"])


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    database: Database = request.app.state.database
    async with database.session() as session:
        yield session


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TailoredResumeService:
    return TailoredResumeService(
        SqlAlchemyCandidateProfileRepository(session),
        SqlAlchemyJobOfferRepository(session),
        SqlAlchemyMatchAssessmentRepository(session),
        SqlAlchemyTailoredResumeRepository(session),
    )


Service = Annotated[TailoredResumeService, Depends(get_service)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_tailored_resume(
    payload: TailoredResumeInput, service: Service
) -> TailoredResumeResponse:
    try:
        resume = await service.create(
            payload.candidate_profile_id,
            payload.job_offer_id,
            payload.match_assessment_id,
            use_llm=payload.use_llm,
        )
    except ResumeCandidateNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "candidate_profile_not_found") from error
    except ResumeJobOfferNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job_offer_not_found") from error
    except ResumeMatchAssessmentNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "match_assessment_not_found") from error
    except ResumeAssessmentMismatchError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "match_assessment_mismatch") from error
    except StaleResumeAssessmentError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "match_assessment_stale") from error
    except ResumeLLMNotConfiguredError as error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "resume_llm_not_configured"
        ) from error
    return TailoredResumeResponse.model_validate(resume)


@router.get("/{resume_id}")
async def get_tailored_resume(resume_id: UUID, service: Service) -> TailoredResumeResponse:
    try:
        resume = await service.get(resume_id)
    except TailoredResumeNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "tailored_resume_not_found") from error
    return TailoredResumeResponse.model_validate(resume)


@router.patch("/{resume_id}/review")
async def review_tailored_resume(
    resume_id: UUID, payload: ResumeReviewInput, service: Service
) -> TailoredResumeResponse:
    try:
        resume = await service.review(resume_id, payload.decision)
    except TailoredResumeNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "tailored_resume_not_found") from error
    except TailoredResumeAlreadyReviewedError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "tailored_resume_already_reviewed") from error
    except TailoredResumeReviewConflictError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "tailored_resume_changed") from error
    return TailoredResumeResponse.model_validate(resume)
