"""REST endpoints for manually managed candidate profiles."""

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.candidate.api.schemas import CandidateProfileInput, CandidateProfileResponse
from jobhunter.candidate.application.errors import CandidateProfileNotFoundError
from jobhunter.candidate.application.service import CandidateProfileService
from jobhunter.candidate.infrastructure.database.repository import (
    SqlAlchemyCandidateProfileRepository,
)
from jobhunter.infrastructure.database.session import Database

router = APIRouter(prefix="/candidate-profiles", tags=["candidate profiles"])


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Provide one database session per request."""

    database: Database = request.app.state.database
    async with database.session() as session:
        yield session


def get_service(session: Annotated[AsyncSession, Depends(get_session)]) -> CandidateProfileService:
    """Wire the application service to its SQLAlchemy adapter."""

    return CandidateProfileService(SqlAlchemyCandidateProfileRepository(session))


Service = Annotated[CandidateProfileService, Depends(get_service)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_candidate_profile(
    payload: CandidateProfileInput, service: Service
) -> CandidateProfileResponse:
    """Create a profile from facts explicitly entered by the user."""

    if payload.entity_ids:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "unexpected_entity_id")
    try:
        candidate = payload.to_domain()
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    profile = await service.create(candidate)
    return CandidateProfileResponse.model_validate(profile)


@router.get("/{profile_id}")
async def get_candidate_profile(profile_id: UUID, service: Service) -> CandidateProfileResponse:
    """Return one complete candidate aggregate."""

    try:
        profile = await service.get(profile_id)
    except CandidateProfileNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "candidate_profile_not_found") from error
    return CandidateProfileResponse.model_validate(profile)


@router.put("/{profile_id}")
async def replace_candidate_profile(
    profile_id: UUID, payload: CandidateProfileInput, service: Service
) -> CandidateProfileResponse:
    """Replace the aggregate while retaining its root identity and creation time."""

    try:
        existing = await service.get(profile_id)
        if not payload.entity_ids.issubset(existing.entity_ids):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "unknown_entity_id")
        try:
            candidate = payload.to_domain(profile_id=profile_id, created_at=existing.created_at)
        except ValueError as error:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
        profile = await service.replace(candidate)
    except CandidateProfileNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "candidate_profile_not_found") from error
    return CandidateProfileResponse.model_validate(profile)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate_profile(profile_id: UUID, service: Service) -> Response:
    """Delete a candidate profile and all facts owned by it."""

    try:
        await service.delete(profile_id)
    except CandidateProfileNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "candidate_profile_not_found") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
