"""Add versioned structured match assessments.

Revision ID: 20260813_0007
Revises: 20260813_0006
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_0007"
down_revision: str | None = "20260813_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "match_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_profile_id", sa.Uuid(), nullable=False),
        sa.Column("job_offer_id", sa.Uuid(), nullable=False),
        sa.Column("policy_version", sa.String(length=50), nullable=False),
        sa.Column("taxonomy_version", sa.String(length=50), nullable=False),
        sa.Column("candidate_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("job_content_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("job_normalization_version", sa.String(length=20), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column(
            "recommendation",
            sa.Enum(
                "strong_match",
                "good_match",
                "weak_match",
                "blocked",
                "needs_review",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "score >= 0 AND score <= 100", name=op.f("ck_match_assessments_score_range")
        ),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"], ["candidate_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["job_offer_id"], ["job_offers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_match_assessments_candidate_profile_id"),
        "match_assessments",
        ["candidate_profile_id"],
    )
    op.create_index(
        op.f("ix_match_assessments_job_offer_id"), "match_assessments", ["job_offer_id"]
    )
    op.create_table(
        "match_dimensions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "name",
            sa.Enum(
                "skills",
                "experience",
                "seniority",
                "education",
                "languages",
                "location",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)",
            name=op.f("ck_match_dimensions_score_range"),
        ),
        sa.CheckConstraint(
            "weight > 0 AND weight <= 1", name=op.f("ck_match_dimensions_weight_range")
        ),
        sa.ForeignKeyConstraint(["assessment_id"], ["match_assessments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assessment_id", "name", name="uq_match_dimensions_assessment_name"),
        sa.UniqueConstraint(
            "assessment_id", "position", name="uq_match_dimensions_assessment_position"
        ),
    )
    op.create_index(
        op.f("ix_match_dimensions_assessment_id"), "match_dimensions", ["assessment_id"]
    )
    op.create_table(
        "match_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dimension_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "outcome",
            sa.Enum("matched", "partial", "missing", "unknown", native_enum=False),
            nullable=False,
        ),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("explanation_code", sa.String(length=100), nullable=False),
        sa.Column("job_value", sa.String(length=2000), nullable=False),
        sa.Column("candidate_fact_ids", sa.JSON(), nullable=False),
        sa.Column("candidate_values", sa.JSON(), nullable=False),
        sa.Column("job_requirement_id", sa.Uuid(), nullable=True),
        sa.Column("job_field_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)",
            name=op.f("ck_match_evidence_score_range"),
        ),
        sa.CheckConstraint(
            "(job_requirement_id IS NOT NULL AND job_field_id IS NULL) OR "
            "(job_requirement_id IS NULL AND job_field_id IS NOT NULL)",
            name=op.f("ck_match_evidence_one_job_fact"),
        ),
        sa.ForeignKeyConstraint(["dimension_id"], ["match_dimensions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_field_id"], ["job_offer_fields.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["job_requirement_id"], ["job_requirements.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dimension_id", "position", name="uq_match_evidence_dimension_position"
        ),
    )
    op.create_index(op.f("ix_match_evidence_dimension_id"), "match_evidence", ["dimension_id"])
    op.create_index(op.f("ix_match_evidence_job_field_id"), "match_evidence", ["job_field_id"])
    op.create_index(
        op.f("ix_match_evidence_job_requirement_id"), "match_evidence", ["job_requirement_id"]
    )
    op.create_table(
        "match_requirement_gates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("job_requirement_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("passed", "failed", "needs_review", native_enum=False),
            nullable=False,
        ),
        sa.Column("explanation_code", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["match_assessments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["job_requirement_id"], ["job_requirements.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assessment_id", "job_requirement_id", name="uq_match_gates_assessment_requirement"
        ),
        sa.UniqueConstraint("assessment_id", "position", name="uq_match_gates_assessment_position"),
    )
    op.create_index(
        op.f("ix_match_requirement_gates_assessment_id"),
        "match_requirement_gates",
        ["assessment_id"],
    )
    op.create_index(
        op.f("ix_match_requirement_gates_job_requirement_id"),
        "match_requirement_gates",
        ["job_requirement_id"],
    )


def downgrade() -> None:
    op.drop_table("match_requirement_gates")
    op.drop_table("match_evidence")
    op.drop_table("match_dimensions")
    op.drop_table("match_assessments")
