"""Unit tests for candidate profile use cases."""

from collections.abc import Awaitable
from uuid import UUID, uuid4

import pytest

from jobhunter.candidate.application.errors import (
    CandidateProfileAlreadyExistsError,
    CandidateProfileNotFoundError,
)
from jobhunter.candidate.application.service import CandidateProfileService
from jobhunter.candidate.domain.profile import CandidateProfile
from tests.candidate.factories import make_profile


class InMemoryCandidateRepository:
    """Small test adapter implementing the repository port."""

    def __init__(self) -> None:
        self.profiles: dict[UUID, CandidateProfile] = {}

    async def add(self, profile: CandidateProfile) -> CandidateProfile:
        self.profiles[profile.id] = profile
        return profile

    async def get(self, profile_id: UUID) -> CandidateProfile | None:
        return self.profiles.get(profile_id)

    async def replace(self, profile: CandidateProfile) -> CandidateProfile | None:
        if profile.id not in self.profiles:
            return None
        self.profiles[profile.id] = profile
        return profile

    async def delete(self, profile_id: UUID) -> bool:
        return self.profiles.pop(profile_id, None) is not None


@pytest.mark.asyncio
async def test_service_manages_profile_lifecycle() -> None:
    repository = InMemoryCandidateRepository()
    service = CandidateProfileService(repository)
    profile = make_profile()

    assert await service.create(profile) == profile
    assert await service.get(profile.id) == profile

    replacement = make_profile(profile_id=profile.id)
    assert await service.replace(replacement) == replacement
    await service.delete(profile.id)
    assert repository.profiles == {}


@pytest.mark.asyncio
async def test_service_rejects_duplicate_profile() -> None:
    repository = InMemoryCandidateRepository()
    service = CandidateProfileService(repository)
    profile = make_profile()
    await service.create(profile)

    with pytest.raises(CandidateProfileAlreadyExistsError):
        await service.create(profile)


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["get", "replace", "delete"])
async def test_service_reports_missing_profile(operation: str) -> None:
    service = CandidateProfileService(InMemoryCandidateRepository())
    profile = make_profile(profile_id=uuid4())

    coroutine: Awaitable[object]
    if operation == "get":
        coroutine = service.get(profile.id)
    elif operation == "replace":
        coroutine = service.replace(profile)
    else:
        coroutine = service.delete(profile.id)

    with pytest.raises(CandidateProfileNotFoundError):
        await coroutine
