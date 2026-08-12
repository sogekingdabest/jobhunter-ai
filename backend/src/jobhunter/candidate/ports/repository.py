"""Persistence contract for candidate profiles."""

from typing import Protocol
from uuid import UUID

from jobhunter.candidate.domain.profile import CandidateProfile


class CandidateProfileRepository(Protocol):
    """Store aggregate roots without leaking persistence details."""

    async def add(self, profile: CandidateProfile) -> CandidateProfile: ...

    async def get(self, profile_id: UUID) -> CandidateProfile | None: ...

    async def replace(self, profile: CandidateProfile) -> CandidateProfile | None: ...

    async def delete(self, profile_id: UUID) -> bool: ...
