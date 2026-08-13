"""Auditable output of a versioned matching policy."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from jobhunter.matching.domain.semantic import SemanticMatchEvidence

MAX_SCORE = 100
FINGERPRINT_LENGTH = 64
STRONG_MATCH_THRESHOLD = 80
GOOD_MATCH_THRESHOLD = 60


class MatchDimensionName(StrEnum):
    SKILLS = "skills"
    EXPERIENCE = "experience"
    SENIORITY = "seniority"
    EDUCATION = "education"
    LANGUAGES = "languages"
    LOCATION = "location"


class MatchOutcome(StrEnum):
    MATCHED = "matched"
    PARTIAL = "partial"
    MISSING = "missing"
    UNKNOWN = "unknown"


class GateStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class MatchRecommendation(StrEnum):
    STRONG_MATCH = "strong_match"
    GOOD_MATCH = "good_match"
    WEAK_MATCH = "weak_match"
    BLOCKED = "blocked"
    NEEDS_REVIEW = "needs_review"


def _validate_score(value: float | None, code: str) -> None:
    if value is not None and not 0 <= value <= MAX_SCORE:
        raise ValueError(code)


@dataclass(frozen=True, slots=True)
class MatchEvidence:
    """One deterministic comparison and the facts used to reach it."""

    id: UUID
    dimension: MatchDimensionName
    outcome: MatchOutcome
    score: float | None
    explanation_code: str
    job_value: str
    candidate_fact_ids: tuple[UUID, ...] = ()
    candidate_values: tuple[str, ...] = ()
    job_requirement_id: UUID | None = None
    job_field_id: UUID | None = None

    def __post_init__(self) -> None:
        _validate_score(self.score, "invalid_match_evidence_score")
        if not self.explanation_code.strip():
            raise ValueError("missing_match_explanation_code")
        if not self.job_value.strip():
            raise ValueError("missing_match_job_value")
        if any(not value.strip() for value in self.candidate_values):
            raise ValueError("empty_match_candidate_value")
        if self.outcome is MatchOutcome.UNKNOWN and self.score is not None:
            raise ValueError("unknown_match_evidence_has_score")
        if self.outcome is not MatchOutcome.UNKNOWN and self.score is None:
            raise ValueError("scored_match_evidence_missing_score")
        if self.job_requirement_id is None and self.job_field_id is None:
            raise ValueError("match_evidence_missing_job_fact")
        if self.job_requirement_id is not None and self.job_field_id is not None:
            raise ValueError("match_evidence_has_multiple_job_facts")
        if len(set(self.candidate_fact_ids)) != len(self.candidate_fact_ids):
            raise ValueError("duplicate_candidate_match_fact")


@dataclass(frozen=True, slots=True)
class MatchDimension:
    """A weighted, independently explainable score component."""

    id: UUID
    name: MatchDimensionName
    score: float | None
    weight: float
    evidence: tuple[MatchEvidence, ...]

    def __post_init__(self) -> None:
        _validate_score(self.score, "invalid_match_dimension_score")
        if not 0 < self.weight <= 1:
            raise ValueError("invalid_match_dimension_weight")
        if not self.evidence:
            raise ValueError("empty_match_dimension_evidence")
        if any(item.dimension is not self.name for item in self.evidence):
            raise ValueError("foreign_match_dimension_evidence")
        if len({item.id for item in self.evidence}) != len(self.evidence):
            raise ValueError("duplicate_match_evidence_id")
        scored = [item.score for item in self.evidence if item.score is not None]
        if (self.score is None) != (not scored):
            raise ValueError("inconsistent_match_dimension_score")


@dataclass(frozen=True, slots=True)
class RequirementGate:
    """Decision for one explicitly mandatory job requirement."""

    id: UUID
    job_requirement_id: UUID
    status: GateStatus
    explanation_code: str

    def __post_init__(self) -> None:
        if not self.explanation_code.strip():
            raise ValueError("missing_gate_explanation_code")


@dataclass(frozen=True, slots=True)
class MatchAssessment:
    """Immutable snapshot produced by one policy and taxonomy version."""

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
    semantic_evidence: tuple[SemanticMatchEvidence, ...]
    recommendation: MatchRecommendation
    dimensions: tuple[MatchDimension, ...]
    gates: tuple[RequirementGate, ...]
    assessed_at: datetime

    def __post_init__(self) -> None:  # noqa: PLR0912
        if not self.policy_version.strip() or not self.taxonomy_version.strip():
            raise ValueError("missing_match_version")
        if len(self.job_content_fingerprint) != FINGERPRINT_LENGTH:
            raise ValueError("invalid_match_job_fingerprint")
        _validate_score(self.score, "invalid_match_score")
        _validate_score(self.structured_score, "invalid_structured_match_score")
        _validate_score(self.semantic_score, "invalid_semantic_match_score")
        if not 0 <= self.semantic_weight < 1:
            raise ValueError("invalid_semantic_weight")
        semantic_metadata = (
            self.embedding_provider,
            self.embedding_model,
            self.embedding_revision,
            self.embedding_dimensions,
        )
        has_semantics = self.semantic_score is not None
        if has_semantics != all(value is not None for value in semantic_metadata) or (
            not has_semantics and any(value is not None for value in semantic_metadata)
        ):
            raise ValueError("inconsistent_embedding_metadata")
        if has_semantics != bool(self.semantic_evidence):
            raise ValueError("inconsistent_semantic_evidence")
        if has_semantics != (self.semantic_weight > 0):
            raise ValueError("inconsistent_semantic_weight")
        expected_score = self.structured_score
        if self.semantic_score is not None:
            expected_score = round(
                self.structured_score * (1 - self.semantic_weight)
                + self.semantic_score * self.semantic_weight,
                2,
            )
        if self.score != expected_score:
            raise ValueError("inconsistent_hybrid_match_score")
        if len({item.name for item in self.dimensions}) != len(self.dimensions):
            raise ValueError("duplicate_match_dimension")
        if len({item.id for item in self.dimensions}) != len(self.dimensions):
            raise ValueError("duplicate_match_dimension_id")
        if len({item.job_requirement_id for item in self.gates}) != len(self.gates):
            raise ValueError("duplicate_requirement_gate")
        if any(gate.status is GateStatus.FAILED for gate in self.gates):
            expected = MatchRecommendation.BLOCKED
        elif any(gate.status is GateStatus.NEEDS_REVIEW for gate in self.gates):
            expected = MatchRecommendation.NEEDS_REVIEW
        elif self.score >= STRONG_MATCH_THRESHOLD:
            expected = MatchRecommendation.STRONG_MATCH
        elif self.score >= GOOD_MATCH_THRESHOLD:
            expected = MatchRecommendation.GOOD_MATCH
        else:
            expected = MatchRecommendation.WEAK_MATCH
        if self.recommendation is not expected:
            raise ValueError("inconsistent_match_recommendation")
