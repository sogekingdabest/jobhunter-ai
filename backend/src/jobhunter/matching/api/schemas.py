"""Strict HTTP contracts for explainable match assessments."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from jobhunter.matching.domain.assessments import (
    GateStatus,
    MatchDimensionName,
    MatchOutcome,
    MatchRecommendation,
)


class MatchSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class MatchAssessmentInput(MatchSchema):
    candidate_profile_id: UUID
    job_offer_id: UUID


class MatchEvidenceResponse(MatchSchema):
    id: UUID
    dimension: MatchDimensionName
    outcome: MatchOutcome
    score: float | None
    explanation_code: str
    job_value: str
    candidate_fact_ids: tuple[UUID, ...]
    candidate_values: tuple[str, ...]
    job_requirement_id: UUID | None
    job_field_id: UUID | None


class MatchDimensionResponse(MatchSchema):
    id: UUID
    name: MatchDimensionName
    score: float | None
    weight: float
    evidence: tuple[MatchEvidenceResponse, ...]


class RequirementGateResponse(MatchSchema):
    id: UUID
    job_requirement_id: UUID
    status: GateStatus
    explanation_code: str


class MatchAssessmentResponse(MatchSchema):
    id: UUID
    candidate_profile_id: UUID
    job_offer_id: UUID
    policy_version: str
    taxonomy_version: str
    candidate_updated_at: datetime
    job_content_fingerprint: str
    job_normalization_version: str
    score: float
    recommendation: MatchRecommendation
    dimensions: tuple[MatchDimensionResponse, ...]
    gates: tuple[RequirementGateResponse, ...]
    assessed_at: datetime
