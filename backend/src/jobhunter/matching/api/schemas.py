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
from jobhunter.matching.domain.semantic import SemanticSourceType


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


class SemanticMatchEvidenceResponse(MatchSchema):
    id: UUID
    job_source_type: SemanticSourceType
    job_source_id: UUID
    candidate_source_type: SemanticSourceType
    candidate_source_id: UUID
    similarity: float


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
    structured_score: float
    semantic_score: float | None
    semantic_weight: float
    embedding_provider: str | None
    embedding_model: str | None
    embedding_revision: str | None
    embedding_dimensions: int | None
    semantic_evidence: tuple[SemanticMatchEvidenceResponse, ...]
    recommendation: MatchRecommendation
    dimensions: tuple[MatchDimensionResponse, ...]
    gates: tuple[RequirementGateResponse, ...]
    assessed_at: datetime
