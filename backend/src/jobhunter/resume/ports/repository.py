"""Persistence boundary for tailored resumes."""

from typing import Protocol
from uuid import UUID

from jobhunter.resume.domain.models import TailoredResume


class TailoredResumeRepositoryConflictError(Exception):
    """Optimistic concurrency conflict."""


class TailoredResumeRepository(Protocol):
    async def add(self, resume: TailoredResume) -> TailoredResume: ...

    async def get(self, resume_id: UUID) -> TailoredResume | None: ...

    async def replace(self, resume: TailoredResume) -> TailoredResume | None: ...
