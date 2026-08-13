"""REST endpoints for explicit review of grounded fact proposals."""

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.candidate.api.fact_extraction_schemas import (
    CandidateFactExtractionResponse,
    ProposalReviewInput,
)
from jobhunter.candidate.application.errors import (
    CandidateFactAlreadyReviewedError,
    CandidateFactExtractionNotFoundError,
    CandidateFactProposalNotFoundError,
    CandidateFactReviewConflictError,
)
from jobhunter.candidate.application.fact_extraction import CandidateFactReviewService
from jobhunter.candidate.infrastructure.database.fact_extraction_repository import (
    SqlAlchemyCandidateFactExtractionRepository,
)
from jobhunter.infrastructure.database.session import Database

router = APIRouter(prefix="/candidate-fact-extractions", tags=["candidate fact extraction"])


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Provide one database session per request."""

    database: Database = request.app.state.database
    async with database.session() as session:
        yield session


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CandidateFactReviewService:
    """Wire the review use case without coupling it to an LLM provider."""

    return CandidateFactReviewService(SqlAlchemyCandidateFactExtractionRepository(session))


Service = Annotated[CandidateFactReviewService, Depends(get_service)]


@router.get("/{extraction_id}")
async def get_candidate_fact_extraction(
    extraction_id: UUID, service: Service
) -> CandidateFactExtractionResponse:
    """Return grounded proposals and their exact source quotes."""

    try:
        extraction = await service.get(extraction_id)
    except CandidateFactExtractionNotFoundError as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "candidate_fact_extraction_not_found"
        ) from error
    return CandidateFactExtractionResponse.model_validate(extraction)


@router.patch("/{extraction_id}/proposals/{proposal_id}")
async def review_candidate_fact_proposal(
    extraction_id: UUID,
    proposal_id: UUID,
    payload: ProposalReviewInput,
    service: Service,
) -> CandidateFactExtractionResponse:
    """Accept or reject one proposal without allowing later decision rewrites."""

    try:
        extraction = await service.review(extraction_id, proposal_id, payload.decision)
    except CandidateFactExtractionNotFoundError as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "candidate_fact_extraction_not_found"
        ) from error
    except CandidateFactProposalNotFoundError as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "candidate_fact_proposal_not_found"
        ) from error
    except CandidateFactAlreadyReviewedError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "candidate_fact_already_reviewed") from error
    except CandidateFactReviewConflictError as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "candidate_fact_extraction_changed"
        ) from error
    return CandidateFactExtractionResponse.model_validate(extraction)
