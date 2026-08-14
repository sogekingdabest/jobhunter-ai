"""REST contracts for tailored resume generation and review."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from jobhunter.resume.domain.models import (
    GenerationMethod,
    ResumeSection,
    ResumeSourceType,
    ResumeStatus,
)


class ResumeSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class TailoredResumeInput(ResumeSchema):
    candidate_profile_id: UUID
    job_offer_id: UUID
    match_assessment_id: UUID
    use_llm: bool = False


class ResumeReviewInput(ResumeSchema):
    decision: Literal[ResumeStatus.APPROVED, ResumeStatus.REJECTED]


class ResumeSourceResponse(ResumeSchema):
    id: UUID
    source_type: ResumeSourceType
    source_id: UUID
    evidence_source_id: UUID
    source_text: str


class ResumeFragmentResponse(ResumeSchema):
    id: UUID
    resume_id: UUID
    section: ResumeSection
    position: int
    generated_text: str
    method: GenerationMethod
    sources: tuple[ResumeSourceResponse, ...]


class TailoredResumeResponse(ResumeSchema):
    id: UUID
    candidate_profile_id: UUID
    job_offer_id: UUID
    match_assessment_id: UUID
    generation_version: str
    candidate_updated_at: datetime
    job_content_fingerprint: str
    status: ResumeStatus
    fragments: tuple[ResumeFragmentResponse, ...]
    created_at: datetime
    revision: int
    reviewed_at: datetime | None
    provider: str | None
    model: str | None
