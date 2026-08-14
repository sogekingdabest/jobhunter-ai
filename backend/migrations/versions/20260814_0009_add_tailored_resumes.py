"""add tailored resumes

Revision ID: 20260814_0009
Revises: 20260813_0008
Create Date: 2026-08-14 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260814_0009"
down_revision: str | None = "20260813_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tailored_resumes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_profile_id", sa.Uuid(), nullable=False),
        sa.Column("job_offer_id", sa.Uuid(), nullable=False),
        sa.Column("match_assessment_id", sa.Uuid(), nullable=False),
        sa.Column("generation_version", sa.String(length=50), nullable=False),
        sa.Column("candidate_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("job_content_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum("needs_review", "approved", "rejected", name="resumestatus", native_enum=False),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("model", sa.String(length=200), nullable=True),
        sa.CheckConstraint(
            "char_length(job_content_fingerprint) = 64",
            name=op.f("ck_tailored_resumes_job_fingerprint_length"),
        ),
        sa.CheckConstraint("revision >= 0", name=op.f("ck_tailored_resumes_non_negative_revision")),
        sa.CheckConstraint(
            "(status = 'needs_review' AND reviewed_at IS NULL) OR "
            "(status IN ('approved', 'rejected') AND reviewed_at IS NOT NULL)",
            name=op.f("ck_tailored_resumes_review_state"),
        ),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_tailored_resumes_candidate_profile_id_candidate_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_offer_id"],
            ["job_offers.id"],
            name=op.f("fk_tailored_resumes_job_offer_id_job_offers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["match_assessment_id"],
            ["match_assessments.id"],
            name=op.f("fk_tailored_resumes_match_assessment_id_match_assessments"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tailored_resumes")),
    )
    for column in ("candidate_profile_id", "job_offer_id", "match_assessment_id"):
        op.create_index(op.f(f"ix_tailored_resumes_{column}"), "tailored_resumes", [column])

    op.create_table(
        "tailored_resume_fragments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "section",
            sa.Enum(
                "header",
                "summary",
                "experience",
                "education",
                "projects",
                "skills",
                "languages",
                name="resumesection",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("generated_text", sa.Text(), nullable=False),
        sa.Column(
            "method",
            sa.Enum("extractive", "llm_rephrased", name="generationmethod", native_enum=False),
            nullable=False,
        ),
        sa.CheckConstraint(
            "position >= 0", name=op.f("ck_tailored_resume_fragments_non_negative_position")
        ),
        sa.ForeignKeyConstraint(
            ["resume_id"],
            ["tailored_resumes.id"],
            name=op.f("fk_tailored_resume_fragments_resume_id_tailored_resumes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tailored_resume_fragments")),
        sa.UniqueConstraint("resume_id", "position", name="uq_resume_fragments_resume_position"),
    )
    op.create_index(
        op.f("ix_tailored_resume_fragments_resume_id"),
        "tailored_resume_fragments",
        ["resume_id"],
    )

    op.create_table(
        "tailored_resume_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("fragment_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum(
                "profile",
                "work_experience",
                "education",
                "project",
                "competency",
                "language",
                name="resumesourcetype",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_source_id", sa.Uuid(), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "position >= 0", name=op.f("ck_tailored_resume_sources_non_negative_position")
        ),
        sa.ForeignKeyConstraint(
            ["evidence_source_id"],
            ["evidence_sources.id"],
            name=op.f("fk_tailored_resume_sources_evidence_source_id_evidence_sources"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["fragment_id"],
            ["tailored_resume_fragments.id"],
            name=op.f("fk_tailored_resume_sources_fragment_id_tailored_resume_fragments"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tailored_resume_sources")),
        sa.UniqueConstraint("fragment_id", "position", name="uq_resume_sources_fragment_position"),
        sa.UniqueConstraint(
            "fragment_id", "source_type", "source_id", name="uq_resume_sources_fact"
        ),
    )
    op.create_index(
        op.f("ix_tailored_resume_sources_evidence_source_id"),
        "tailored_resume_sources",
        ["evidence_source_id"],
    )
    op.create_index(
        op.f("ix_tailored_resume_sources_fragment_id"),
        "tailored_resume_sources",
        ["fragment_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_tailored_resume_sources_fragment_id"), table_name="tailored_resume_sources"
    )
    op.drop_index(
        op.f("ix_tailored_resume_sources_evidence_source_id"),
        table_name="tailored_resume_sources",
    )
    op.drop_table("tailored_resume_sources")
    op.drop_index(
        op.f("ix_tailored_resume_fragments_resume_id"),
        table_name="tailored_resume_fragments",
    )
    op.drop_table("tailored_resume_fragments")
    for column in ("match_assessment_id", "job_offer_id", "candidate_profile_id"):
        op.drop_index(op.f(f"ix_tailored_resumes_{column}"), table_name="tailored_resumes")
    op.drop_table("tailored_resumes")
