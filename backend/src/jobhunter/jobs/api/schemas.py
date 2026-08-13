"""Validated API contracts for manual job offer imports."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from jobhunter.ai.contracts.job_offers import JobOfferNormalizationOutput
from jobhunter.jobs.domain.offers import (
    EmploymentType,
    JobFieldName,
    JobSource,
    RemoteType,
    RequirementPriority,
    RequirementType,
    Seniority,
)


class JobSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ManualJobOfferInput(JobSchema):
    """Pasted source plus untrusted structured output from any supported runtime."""

    raw_text: Annotated[str, Field(min_length=1, max_length=100_000)]
    normalization: JobOfferNormalizationOutput


class JobUrlPreviewInput(JobSchema):
    url: Annotated[str, Field(min_length=1, max_length=2_048)]


class JobUrlPreviewResponse(JobSchema):
    requested_url: str
    final_url: str
    canonical_url: str
    raw_text: str
    content_fingerprint: Annotated[str, Field(min_length=64, max_length=64)]
    media_type: str


class JobUrlImportInput(JobUrlPreviewInput):
    expected_content_fingerprint: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    normalization: JobOfferNormalizationOutput


class JobOfferFieldResponse(JobSchema):
    id: UUID
    evidence_span_id: UUID
    name: JobFieldName
    value: str
    evidence_quote: str
    start_offset: int
    end_offset: int
    confidence: float


class JobRequirementResponse(JobSchema):
    id: UUID
    evidence_span_id: UUID
    requirement_type: RequirementType
    priority: RequirementPriority
    normalized_value: str
    original_text: str
    start_offset: int
    end_offset: int
    confidence: float


class JobOfferResponse(JobSchema):
    """Normalized offer with exact evidence exposed for audit and UI."""

    id: UUID
    evidence_source_id: UUID
    source: JobSource
    source_url: str | None
    canonical_url: str | None
    raw_text: str
    content_fingerprint: str
    normalization_version: str
    company: str | None
    title: str | None
    location: str | None
    remote_type: RemoteType | None
    employment_type: EmploymentType | None
    seniority: Seniority | None
    fields: tuple[JobOfferFieldResponse, ...]
    requirements: tuple[JobRequirementResponse, ...]
    warnings: tuple[str, ...]
    discovered_at: datetime
