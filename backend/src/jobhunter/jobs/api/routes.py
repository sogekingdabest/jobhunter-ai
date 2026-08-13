"""REST endpoints for grounded manual job offer imports."""

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.infrastructure.database.session import Database
from jobhunter.jobs.api.schemas import JobOfferResponse, ManualJobOfferInput
from jobhunter.jobs.application.errors import (
    DuplicateJobOfferError,
    JobOfferNotFoundError,
    UngroundedJobNormalizationError,
)
from jobhunter.jobs.application.normalization import ManualJobOfferService
from jobhunter.jobs.infrastructure.database.repository import SqlAlchemyJobOfferRepository

router = APIRouter(prefix="/job-offers", tags=["job offers"])


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    database: Database = request.app.state.database
    async with database.session() as session:
        yield session


def get_service(session: Annotated[AsyncSession, Depends(get_session)]) -> ManualJobOfferService:
    return ManualJobOfferService(SqlAlchemyJobOfferRepository(session))


Service = Annotated[ManualJobOfferService, Depends(get_service)]


@router.post("/manual", status_code=status.HTTP_201_CREATED)
async def import_manual_job_offer(
    payload: ManualJobOfferInput, service: Service
) -> JobOfferResponse:
    """Persist pasted content only after exact-evidence normalization validation."""

    try:
        offer = await service.import_normalized(payload.raw_text, payload.normalization)
    except DuplicateJobOfferError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "duplicate_job_offer") from error
    except UngroundedJobNormalizationError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "ungrounded_job_normalization"
        ) from error
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    return JobOfferResponse.model_validate(offer)


@router.get("/{offer_id}")
async def get_job_offer(offer_id: UUID, service: Service) -> JobOfferResponse:
    """Return one normalized offer and its source evidence."""

    try:
        offer = await service.get(offer_id)
    except JobOfferNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job_offer_not_found") from error
    return JobOfferResponse.model_validate(offer)
