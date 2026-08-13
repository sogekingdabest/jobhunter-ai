"""Persistence boundary for immutable match assessments."""

from typing import Protocol
from uuid import UUID

from jobhunter.matching.domain.assessments import MatchAssessment


class MatchAssessmentRepository(Protocol):
    async def add(self, assessment: MatchAssessment) -> MatchAssessment: ...

    async def get(self, assessment_id: UUID) -> MatchAssessment | None: ...
