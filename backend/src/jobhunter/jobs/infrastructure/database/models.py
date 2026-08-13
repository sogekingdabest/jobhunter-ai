"""Relational models for normalized job offers and grounded requirements."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jobhunter.candidate.infrastructure.database.models import domain_enum
from jobhunter.documents.infrastructure.database.models import EvidenceSpanModel
from jobhunter.infrastructure.database.base import Base
from jobhunter.jobs.domain.offers import (
    JobFieldName,
    JobSource,
    RequirementPriority,
    RequirementType,
)


class JobOfferModel(Base):
    """Manual source content and normalization metadata."""

    __tablename__ = "job_offers"
    __table_args__ = (
        CheckConstraint("length(raw_text) > 0", name="raw_text_present"),
        CheckConstraint("content_fingerprint ~ '^[0-9a-f]{64}$'", name="fingerprint_format"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    evidence_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_sources.id", ondelete="RESTRICT"), unique=True
    )
    source: Mapped[JobSource] = mapped_column(domain_enum(JobSource))
    raw_text: Mapped[str] = mapped_column(Text)
    content_fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    normalization_version: Mapped[str] = mapped_column(String(20))
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fields: Mapped[list[JobOfferFieldModel]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="JobOfferFieldModel.position",
    )
    requirements: Mapped[list[JobRequirementModel]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="JobRequirementModel.position",
    )


class JobOfferFieldModel(Base):
    """Persisted normalized scalar and its evidence link."""

    __tablename__ = "job_offer_fields"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        UniqueConstraint("job_offer_id", "name", name="uq_job_offer_fields_offer_name"),
        UniqueConstraint("job_offer_id", "position", name="uq_job_offer_fields_offer_position"),
        UniqueConstraint("evidence_span_id", name="uq_job_offer_fields_evidence_span"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    job_offer_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_offers.id", ondelete="CASCADE"), index=True
    )
    evidence_span_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_spans.id", ondelete="RESTRICT")
    )
    evidence_span: Mapped[EvidenceSpanModel] = relationship(lazy="joined")
    position: Mapped[int] = mapped_column(Integer)
    name: Mapped[JobFieldName] = mapped_column(domain_enum(JobFieldName))
    value: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)


class JobRequirementModel(Base):
    """Persisted classified requirement and its exact evidence."""

    __tablename__ = "job_requirements"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        UniqueConstraint("job_offer_id", "position", name="uq_job_requirements_offer_position"),
        UniqueConstraint("evidence_span_id", name="uq_job_requirements_evidence_span"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    job_offer_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_offers.id", ondelete="CASCADE"), index=True
    )
    evidence_span_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_spans.id", ondelete="RESTRICT")
    )
    evidence_span: Mapped[EvidenceSpanModel] = relationship(lazy="joined")
    position: Mapped[int] = mapped_column(Integer)
    requirement_type: Mapped[RequirementType] = mapped_column(domain_enum(RequirementType))
    priority: Mapped[RequirementPriority] = mapped_column(domain_enum(RequirementPriority))
    normalized_value: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
