"""Relational models for traceable tailored resumes."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jobhunter.candidate.infrastructure.database.models import domain_enum
from jobhunter.infrastructure.database.base import Base
from jobhunter.resume.domain.models import (
    GenerationMethod,
    ResumeSection,
    ResumeSourceType,
    ResumeStatus,
)


class TailoredResumeModel(Base):
    __tablename__ = "tailored_resumes"
    __table_args__ = (
        CheckConstraint("revision >= 0", name="non_negative_revision"),
        CheckConstraint(
            "(status = 'needs_review' AND reviewed_at IS NULL) OR "
            "(status IN ('approved', 'rejected') AND reviewed_at IS NOT NULL)",
            name="review_state",
        ),
        CheckConstraint("char_length(job_content_fingerprint) = 64", name="job_fingerprint_length"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    candidate_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    job_offer_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_offers.id", ondelete="CASCADE"), index=True
    )
    match_assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("match_assessments.id", ondelete="RESTRICT"), index=True
    )
    generation_version: Mapped[str] = mapped_column(String(50))
    candidate_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    job_content_fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[ResumeStatus] = mapped_column(domain_enum(ResumeStatus))
    revision: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(200))
    fragments: Mapped[list[ResumeFragmentModel]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ResumeFragmentModel.position",
    )


class ResumeFragmentModel(Base):
    __tablename__ = "tailored_resume_fragments"
    __table_args__ = (
        CheckConstraint("position >= 0", name="non_negative_position"),
        UniqueConstraint("resume_id", "position", name="uq_resume_fragments_resume_position"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    resume_id: Mapped[UUID] = mapped_column(
        ForeignKey("tailored_resumes.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    section: Mapped[ResumeSection] = mapped_column(domain_enum(ResumeSection))
    generated_text: Mapped[str] = mapped_column(Text)
    method: Mapped[GenerationMethod] = mapped_column(domain_enum(GenerationMethod))
    sources: Mapped[list[ResumeSourceModel]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ResumeSourceModel.position",
    )


class ResumeSourceModel(Base):
    __tablename__ = "tailored_resume_sources"
    __table_args__ = (
        CheckConstraint("position >= 0", name="non_negative_position"),
        UniqueConstraint("fragment_id", "position", name="uq_resume_sources_fragment_position"),
        UniqueConstraint("fragment_id", "source_type", "source_id", name="uq_resume_sources_fact"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    fragment_id: Mapped[UUID] = mapped_column(
        ForeignKey("tailored_resume_fragments.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    source_type: Mapped[ResumeSourceType] = mapped_column(domain_enum(ResumeSourceType))
    source_id: Mapped[UUID] = mapped_column(Uuid)
    evidence_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_sources.id", ondelete="RESTRICT"), index=True
    )
    source_text: Mapped[str] = mapped_column(Text)
