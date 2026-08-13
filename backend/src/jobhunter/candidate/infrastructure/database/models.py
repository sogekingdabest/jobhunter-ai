"""Relational models for the candidate profile aggregate."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jobhunter.candidate.domain.competencies import CompetencyCategory, LanguageLevel
from jobhunter.candidate.domain.facts import (
    CandidateFactType,
    ExtractionStatus,
    ProposalReviewStatus,
)
from jobhunter.candidate.domain.profile import RemotePreference
from jobhunter.documents.infrastructure.database.models import EvidenceSpanModel
from jobhunter.infrastructure.database.base import Base


def domain_enum(enum_type: type[StrEnum]) -> Enum:
    """Persist StrEnum values rather than Python member names."""

    return Enum(
        enum_type,
        native_enum=False,
        values_callable=lambda values: [item.value for item in values],
    )


class CandidateProfileModel(Base):
    """Database representation of the candidate aggregate root."""

    __tablename__ = "candidate_profiles"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    evidence_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_sources.id", ondelete="RESTRICT"), index=True
    )
    full_name: Mapped[str] = mapped_column(String(200))
    headline: Mapped[str | None] = mapped_column(String(250))
    summary: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(50))
    location: Mapped[str | None] = mapped_column(String(200))
    remote_preference: Mapped[RemotePreference | None] = mapped_column(
        domain_enum(RemotePreference)
    )
    preferred_roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferred_locations: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    work_experiences: Mapped[list[WorkExperienceModel]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )
    education: Mapped[list[EducationModel]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )
    projects: Mapped[list[ProjectModel]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )
    competencies: Mapped[list[CompetencyModel]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )
    languages: Mapped[list[LanguageProficiencyModel]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class CandidateChild:
    """Shared columns for entities owned by a candidate profile."""

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    candidate_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    evidence_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_sources.id", ondelete="RESTRICT"), index=True
    )


class WorkExperienceModel(CandidateChild, Base):
    """Persisted employment entry."""

    __tablename__ = "candidate_work_experiences"
    __table_args__ = (
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="valid_date_range",
        ),
    )

    employer: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(200))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)


class EducationModel(CandidateChild, Base):
    """Persisted education entry."""

    __tablename__ = "candidate_education"
    __table_args__ = (
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="valid_date_range",
        ),
    )

    institution: Mapped[str] = mapped_column(String(200))
    qualification: Mapped[str] = mapped_column(String(200))
    field_of_study: Mapped[str | None] = mapped_column(String(200))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)


class ProjectModel(CandidateChild, Base):
    """Persisted project entry."""

    __tablename__ = "candidate_projects"

    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(2048))


class CompetencyModel(CandidateChild, Base):
    """Persisted candidate competency."""

    __tablename__ = "candidate_competencies"
    __table_args__ = (
        CheckConstraint(
            "months_experience IS NULL OR months_experience >= 0",
            name="non_negative_months_experience",
        ),
    )

    name: Mapped[str] = mapped_column(String(150))
    category: Mapped[CompetencyCategory] = mapped_column(domain_enum(CompetencyCategory))
    months_experience: Mapped[int | None] = mapped_column(Integer)


class LanguageProficiencyModel(CandidateChild, Base):
    """Persisted human-language proficiency."""

    __tablename__ = "candidate_languages"

    language: Mapped[str] = mapped_column(String(100))
    level: Mapped[LanguageLevel] = mapped_column(domain_enum(LanguageLevel))


class CandidateFactExtractionModel(Base):
    """Persisted model invocation whose grounded proposals require human review."""

    __tablename__ = "candidate_fact_extractions"
    __table_args__ = (
        CheckConstraint(
            "(status = 'needs_review' AND completed_at IS NULL) OR "
            "(status = 'reviewed' AND completed_at IS NOT NULL)",
            name="completion_state",
        ),
        CheckConstraint("revision >= 0", name="non_negative_revision"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    source_document_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_documents.id", ondelete="RESTRICT"), index=True
    )
    evidence_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_sources.id", ondelete="RESTRICT"), unique=True
    )
    contract_version: Mapped[str] = mapped_column(String(20))
    provider: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(200))
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[ExtractionStatus] = mapped_column(domain_enum(ExtractionStatus))
    revision: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    proposals: Mapped[list[CandidateFactProposalModel]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="CandidateFactProposalModel.position",
    )


class CandidateFactProposalModel(Base):
    """One exact-evidence-backed proposal and its irreversible review decision."""

    __tablename__ = "candidate_fact_proposals"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        CheckConstraint(
            "(review_status = 'needs_review' AND reviewed_at IS NULL) OR "
            "(review_status IN ('accepted', 'rejected') AND reviewed_at IS NOT NULL)",
            name="review_state",
        ),
        UniqueConstraint(
            "extraction_id",
            "position",
            name="uq_candidate_fact_proposals_extraction_position",
        ),
        UniqueConstraint("evidence_span_id", name="uq_candidate_fact_proposals_evidence_span"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    extraction_id: Mapped[UUID] = mapped_column(
        ForeignKey("candidate_fact_extractions.id", ondelete="CASCADE"), index=True
    )
    evidence_span_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_spans.id", ondelete="RESTRICT")
    )
    evidence_span: Mapped[EvidenceSpanModel] = relationship(lazy="joined")
    position: Mapped[int] = mapped_column(Integer)
    fact_type: Mapped[CandidateFactType] = mapped_column(domain_enum(CandidateFactType))
    value: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    review_status: Mapped[ProposalReviewStatus] = mapped_column(domain_enum(ProposalReviewStatus))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
