"""Use cases for manual candidate profile management."""

from uuid import UUID

from jobhunter.candidate.application.errors import (
    CandidateProfileAlreadyExistsError,
    CandidateProfileNotFoundError,
)
from jobhunter.candidate.domain.profile import CandidateProfile
from jobhunter.candidate.ports.repository import CandidateProfileRepository


class CandidateProfileService:
    """Coordinate candidate profile CRUD through the repository port."""

    def __init__(self, repository: CandidateProfileRepository) -> None:
        self._repository = repository

    async def create(self, profile: CandidateProfile) -> CandidateProfile:
        if await self._repository.get(profile.id) is not None:
            raise CandidateProfileAlreadyExistsError
        return await self._repository.add(profile)

    async def get(self, profile_id: UUID) -> CandidateProfile:
        profile = await self._repository.get(profile_id)
        if profile is None:
            raise CandidateProfileNotFoundError
        return profile

    async def replace(self, profile: CandidateProfile) -> CandidateProfile:
        replaced = await self._repository.replace(profile)
        if replaced is None:
            raise CandidateProfileNotFoundError
        return replaced

    async def delete(self, profile_id: UUID) -> None:
        if not await self._repository.delete(profile_id):
            raise CandidateProfileNotFoundError
