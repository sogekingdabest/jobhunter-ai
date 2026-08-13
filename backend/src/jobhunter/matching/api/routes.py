"""REST endpoints for persisted structured match assessments."""

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
from jobhunter.matching.api.schemas import MatchAssessmentInput, MatchAssessmentResponse
from jobhunter.matching.application.errors import (
    MatchAssessmentNotFoundError,
    MatchCandidateNotFoundError,
    MatchJobOfferNotFoundError,
)
from jobhunter.matching.application.service import MatchingService
from jobhunter.matching.infrastructure.database.repository import (
    SqlAlchemyMatchAssessmentRepository,
)

router = APIRouter(prefix="/match-assessments", tags=["matching"])


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    database: Database = request.app.state.database
    async with database.session() as session:
        yield session


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MatchingService:
    return MatchingService(
        SqlAlchemyCandidateProfileRepository(session),
        SqlAlchemyJobOfferRepository(session),
        SqlAlchemyMatchAssessmentRepository(session),
    )


Service = Annotated[MatchingService, Depends(get_service)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_match_assessment(
    payload: MatchAssessmentInput, service: Service
) -> MatchAssessmentResponse:
    try:
        assessment = await service.assess(payload.candidate_profile_id, payload.job_offer_id)
    except MatchCandidateNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "candidate_profile_not_found") from error
    except MatchJobOfferNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job_offer_not_found") from error
    return MatchAssessmentResponse.model_validate(assessment)


@router.get("/{assessment_id}")
async def get_match_assessment(assessment_id: UUID, service: Service) -> MatchAssessmentResponse:
    try:
        assessment = await service.get(assessment_id)
    except MatchAssessmentNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "match_assessment_not_found") from error
    return MatchAssessmentResponse.model_validate(assessment)
