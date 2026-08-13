"""Add grounded candidate fact extraction review queue.

Revision ID: 20260813_0004
Revises: 20260812_0003
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_0004"
down_revision: str | None = "20260812_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create extraction and proposal review tables."""

    op.create_table(
        "candidate_fact_extractions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_document_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_source_id", sa.Uuid(), nullable=False),
        sa.Column("contract_version", sa.String(length=20), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("needs_review", "reviewed", native_enum=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(status = 'needs_review' AND completed_at IS NULL) OR "
            "(status = 'reviewed' AND completed_at IS NOT NULL)",
            name=op.f("ck_candidate_fact_extractions_completion_state"),
        ),
        sa.CheckConstraint(
            "revision >= 0", name=op.f("ck_candidate_fact_extractions_non_negative_revision")
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"], ["source_documents.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["evidence_source_id"], ["evidence_sources.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evidence_source_id"),
    )
    op.create_index(
        "ix_candidate_fact_extractions_source_document_id",
        "candidate_fact_extractions",
        ["source_document_id"],
    )
    op.create_table(
        "candidate_fact_proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("extraction_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_span_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "fact_type",
            sa.Enum(
                "work_experience",
                "education",
                "project",
                "certification",
                "competency",
                "language",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "review_status",
            sa.Enum("needs_review", "accepted", "rejected", native_enum=False),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name=op.f("ck_candidate_fact_proposals_confidence_range"),
        ),
        sa.CheckConstraint(
            "(review_status = 'needs_review' AND reviewed_at IS NULL) OR "
            "(review_status IN ('accepted', 'rejected') AND reviewed_at IS NOT NULL)",
            name=op.f("ck_candidate_fact_proposals_review_state"),
        ),
        sa.ForeignKeyConstraint(
            ["extraction_id"], ["candidate_fact_extractions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["evidence_span_id"], ["evidence_spans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "extraction_id",
            "position",
            name=op.f("uq_candidate_fact_proposals_extraction_position"),
        ),
        sa.UniqueConstraint(
            "evidence_span_id", name=op.f("uq_candidate_fact_proposals_evidence_span")
        ),
    )
    op.create_index(
        "ix_candidate_fact_proposals_extraction_id",
        "candidate_fact_proposals",
        ["extraction_id"],
    )


def downgrade() -> None:
    """Remove the extraction review queue."""

    op.drop_table("candidate_fact_proposals")
    op.drop_table("candidate_fact_extractions")
