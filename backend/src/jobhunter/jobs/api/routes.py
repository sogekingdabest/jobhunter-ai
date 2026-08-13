"""REST endpoints for grounded manual and URL job offer imports."""

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.infrastructure.database.session import Database
from jobhunter.jobs.api.schemas import (
    JobOfferResponse,
    JobUrlImportInput,
    JobUrlPreviewInput,
    JobUrlPreviewResponse,
    ManualJobOfferInput,
)
from jobhunter.jobs.application.errors import (
    DuplicateJobOfferError,
    InvalidJobUrlContentError,
    JobOfferNotFoundError,
    JobUrlContentChangedError,
    JobUrlFetchError,
    UngroundedJobNormalizationError,
    UnsafeJobUrlError,
)
from jobhunter.jobs.application.normalization import ManualJobOfferService
from jobhunter.jobs.application.url_import import UrlJobOfferService
from jobhunter.jobs.infrastructure.database.repository import SqlAlchemyJobOfferRepository
from jobhunter.jobs.infrastructure.url_fetcher import HttpxJobUrlFetcher, JobUrlFetchLimits

router = APIRouter(prefix="/job-offers", tags=["job offers"])


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    database: Database = request.app.state.database
    async with database.session() as session:
        yield session


def get_service(session: Annotated[AsyncSession, Depends(get_session)]) -> ManualJobOfferService:
    return ManualJobOfferService(SqlAlchemyJobOfferRepository(session))


Service = Annotated[ManualJobOfferService, Depends(get_service)]


def get_url_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UrlJobOfferService:
    settings = request.app.state.settings
    limits = JobUrlFetchLimits(
        max_redirects=settings.job_url_max_redirects,
        max_response_bytes=settings.job_url_max_response_bytes,
        max_extracted_characters=settings.job_url_max_extracted_characters,
        connect_timeout_seconds=settings.job_url_connect_timeout_seconds,
        read_timeout_seconds=settings.job_url_read_timeout_seconds,
        total_timeout_seconds=settings.job_url_total_timeout_seconds,
    )
    normalizer = ManualJobOfferService(SqlAlchemyJobOfferRepository(session))
    return UrlJobOfferService(HttpxJobUrlFetcher(limits=limits), normalizer)


UrlService = Annotated[UrlJobOfferService, Depends(get_url_service)]


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


@router.post("/url/preview")
async def preview_job_offer_url(
    payload: JobUrlPreviewInput, service: UrlService
) -> JobUrlPreviewResponse:
    """Return bounded text from a public URL without persisting it."""

    try:
        content = await service.preview(payload.url)
    except UnsafeJobUrlError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "unsafe_job_url") from error
    except InvalidJobUrlContentError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    except JobUrlFetchError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "job_url_fetch_failed") from error
    return JobUrlPreviewResponse.model_validate(content, from_attributes=True)


@router.post("/url", status_code=status.HTTP_201_CREATED)
async def import_job_offer_url(payload: JobUrlImportInput, service: UrlService) -> JobOfferResponse:
    """Refetch and import only the exact URL content previously reviewed."""

    try:
        offer = await service.import_normalized(
            payload.url,
            payload.expected_content_fingerprint,
            payload.normalization,
        )
    except UnsafeJobUrlError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "unsafe_job_url") from error
    except InvalidJobUrlContentError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    except JobUrlFetchError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "job_url_fetch_failed") from error
    except JobUrlContentChangedError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "job_url_content_changed") from error
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
