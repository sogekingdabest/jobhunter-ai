"""Relational models for versioned, explainable match assessments."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jobhunter.candidate.infrastructure.database.models import domain_enum
from jobhunter.infrastructure.database.base import Base
from jobhunter.matching.domain.assessments import (
    GateStatus,
    MatchDimensionName,
    MatchOutcome,
    MatchRecommendation,
)
from jobhunter.matching.domain.semantic import SemanticSourceType


class MatchAssessmentModel(Base):
    __tablename__ = "match_assessments"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="score_range"),
        CheckConstraint(
            "structured_score >= 0 AND structured_score <= 100",
            name="structured_score_range",
        ),
        CheckConstraint(
            "semantic_score IS NULL OR (semantic_score >= 0 AND semantic_score <= 100)",
            name="semantic_score_range",
        ),
        CheckConstraint(
            "semantic_weight >= 0 AND semantic_weight < 1", name="semantic_weight_range"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    candidate_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    job_offer_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_offers.id", ondelete="CASCADE"), index=True
    )
    policy_version: Mapped[str] = mapped_column(String(50))
    taxonomy_version: Mapped[str] = mapped_column(String(50))
    candidate_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    job_content_fingerprint: Mapped[str] = mapped_column(String(64))
    job_normalization_version: Mapped[str] = mapped_column(String(20))
    score: Mapped[float] = mapped_column(Float)
    structured_score: Mapped[float] = mapped_column(Float)
    semantic_score: Mapped[float | None] = mapped_column(Float)
    semantic_weight: Mapped[float] = mapped_column(Float)
    embedding_provider: Mapped[str | None] = mapped_column(String(100))
    embedding_model: Mapped[str | None] = mapped_column(String(200))
    embedding_revision: Mapped[str | None] = mapped_column(String(100))
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer)
    recommendation: Mapped[MatchRecommendation] = mapped_column(domain_enum(MatchRecommendation))
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    dimensions: Mapped[list[MatchDimensionModel]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="MatchDimensionModel.position",
    )
    gates: Mapped[list[RequirementGateModel]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="RequirementGateModel.position",
    )
    semantic_evidence: Mapped[list[SemanticMatchEvidenceModel]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="SemanticMatchEvidenceModel.position",
    )


class MatchDimensionModel(Base):
    __tablename__ = "match_dimensions"
    __table_args__ = (
        CheckConstraint("score IS NULL OR (score >= 0 AND score <= 100)", name="score_range"),
        CheckConstraint("weight > 0 AND weight <= 1", name="weight_range"),
        UniqueConstraint("assessment_id", "name", name="uq_match_dimensions_assessment_name"),
        UniqueConstraint(
            "assessment_id", "position", name="uq_match_dimensions_assessment_position"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("match_assessments.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    name: Mapped[MatchDimensionName] = mapped_column(domain_enum(MatchDimensionName))
    score: Mapped[float | None] = mapped_column(Float)
    weight: Mapped[float] = mapped_column(Float)
    evidence: Mapped[list[MatchEvidenceModel]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="MatchEvidenceModel.position",
    )


class MatchEvidenceModel(Base):
    __tablename__ = "match_evidence"
    __table_args__ = (
        CheckConstraint("score IS NULL OR (score >= 0 AND score <= 100)", name="score_range"),
        CheckConstraint(
            "(job_requirement_id IS NOT NULL AND job_field_id IS NULL) OR "
            "(job_requirement_id IS NULL AND job_field_id IS NOT NULL)",
            name="one_job_fact",
        ),
        UniqueConstraint("dimension_id", "position", name="uq_match_evidence_dimension_position"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    dimension_id: Mapped[UUID] = mapped_column(
        ForeignKey("match_dimensions.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    outcome: Mapped[MatchOutcome] = mapped_column(domain_enum(MatchOutcome))
    score: Mapped[float | None] = mapped_column(Float)
    explanation_code: Mapped[str] = mapped_column(String(100))
    job_value: Mapped[str] = mapped_column(String(2000))
    candidate_fact_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    candidate_values: Mapped[list[str]] = mapped_column(JSON, default=list)
    job_requirement_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("job_requirements.id", ondelete="CASCADE"), index=True
    )
    job_field_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("job_offer_fields.id", ondelete="CASCADE"), index=True
    )


class RequirementGateModel(Base):
    __tablename__ = "match_requirement_gates"
    __table_args__ = (
        UniqueConstraint(
            "assessment_id", "job_requirement_id", name="uq_match_gates_assessment_requirement"
        ),
        UniqueConstraint("assessment_id", "position", name="uq_match_gates_assessment_position"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("match_assessments.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    job_requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_requirements.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[GateStatus] = mapped_column(domain_enum(GateStatus))
    explanation_code: Mapped[str] = mapped_column(String(100))


class SemanticMatchEvidenceModel(Base):
    __tablename__ = "match_semantic_evidence"
    __table_args__ = (
        CheckConstraint("similarity >= 0 AND similarity <= 1", name="similarity_range"),
        UniqueConstraint(
            "assessment_id", "position", name="uq_match_semantic_evidence_assessment_position"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("match_assessments.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    job_source_type: Mapped[SemanticSourceType] = mapped_column(domain_enum(SemanticSourceType))
    job_source_id: Mapped[UUID] = mapped_column(Uuid)
    candidate_source_type: Mapped[SemanticSourceType] = mapped_column(
        domain_enum(SemanticSourceType)
    )
    candidate_source_id: Mapped[UUID] = mapped_column(Uuid)
    similarity: Mapped[float] = mapped_column(Float)


class SemanticEmbeddingModel(Base):
    __tablename__ = "semantic_embeddings"
    __table_args__ = (
        CheckConstraint(
            "(candidate_profile_id IS NOT NULL AND job_offer_id IS NULL) OR "
            "(candidate_profile_id IS NULL AND job_offer_id IS NOT NULL)",
            name="one_embedding_scope",
        ),
        CheckConstraint("dimensions > 0 AND dimensions <= 2000", name="dimensions_range"),
        CheckConstraint("vector_dims(embedding) = dimensions", name="embedding_dimensions_match"),
        Index(
            "uq_semantic_embeddings_candidate_cache_key",
            "candidate_profile_id",
            "source_type",
            "source_id",
            "content_hash",
            "provider",
            "model",
            "revision",
            unique=True,
            postgresql_where=text("candidate_profile_id IS NOT NULL"),
        ),
        Index(
            "uq_semantic_embeddings_job_cache_key",
            "job_offer_id",
            "source_type",
            "source_id",
            "content_hash",
            "provider",
            "model",
            "revision",
            unique=True,
            postgresql_where=text("job_offer_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    candidate_profile_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    job_offer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("job_offers.id", ondelete="CASCADE"), index=True
    )
    source_type: Mapped[SemanticSourceType] = mapped_column(domain_enum(SemanticSourceType))
    source_id: Mapped[UUID] = mapped_column(Uuid)
    content_hash: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(200))
    revision: Mapped[str] = mapped_column(String(100))
    dimensions: Mapped[int] = mapped_column(Integer)
    embedding: Mapped[list[float]] = mapped_column(VECTOR())
