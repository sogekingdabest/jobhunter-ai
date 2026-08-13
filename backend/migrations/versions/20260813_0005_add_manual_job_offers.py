"""Add normalized manual job offers.

Revision ID: 20260813_0005
Revises: 20260813_0004
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_0005"
down_revision: str | None = "20260813_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Extend evidence sources and create the jobs aggregate tables."""

    op.drop_constraint(
        op.f("ck_evidence_sources_source_document_type"),
        "evidence_sources",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_evidence_sources_source_document_type"),
        "evidence_sources",
        "(source_type = 'document' AND source_document_id IS NOT NULL) OR "
        "(source_type IN ('user_statement', 'job_offer') "
        "AND source_document_id IS NULL)",
    )
    op.create_table(
        "job_offers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evidence_source_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.Enum("manual", native_enum=False), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("content_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("normalization_version", sa.String(length=20), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "content_fingerprint ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_job_offers_fingerprint_format"),
        ),
        sa.CheckConstraint("length(raw_text) > 0", name=op.f("ck_job_offers_raw_text_present")),
        sa.ForeignKeyConstraint(
            ["evidence_source_id"], ["evidence_sources.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_fingerprint"),
        sa.UniqueConstraint("evidence_source_id"),
    )
    op.create_table(
        "job_offer_fields",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_offer_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_span_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "name",
            sa.Enum(
                "company",
                "title",
                "location",
                "remote_type",
                "employment_type",
                "seniority",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name=op.f("ck_job_offer_fields_confidence_range"),
        ),
        sa.ForeignKeyConstraint(["evidence_span_id"], ["evidence_spans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["job_offer_id"], ["job_offers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_offer_id", "name", name=op.f("uq_job_offer_fields_offer_name")),
        sa.UniqueConstraint(
            "job_offer_id", "position", name=op.f("uq_job_offer_fields_offer_position")
        ),
        sa.UniqueConstraint("evidence_span_id", name=op.f("uq_job_offer_fields_evidence_span")),
    )
    op.create_index("ix_job_offer_fields_job_offer_id", "job_offer_fields", ["job_offer_id"])
    op.create_table(
        "job_requirements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_offer_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_span_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "requirement_type",
            sa.Enum(
                "skill",
                "experience",
                "education",
                "language",
                "location",
                "responsibility",
                "other",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Enum("required", "preferred", "unspecified", native_enum=False),
            nullable=False,
        ),
        sa.Column("normalized_value", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name=op.f("ck_job_requirements_confidence_range"),
        ),
        sa.ForeignKeyConstraint(["evidence_span_id"], ["evidence_spans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["job_offer_id"], ["job_offers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_offer_id", "position", name=op.f("uq_job_requirements_offer_position")
        ),
        sa.UniqueConstraint("evidence_span_id", name=op.f("uq_job_requirements_evidence_span")),
    )
    op.create_index("ix_job_requirements_job_offer_id", "job_requirements", ["job_offer_id"])


def downgrade() -> None:
    """Remove job offers and restore the previous evidence source rule."""

    op.drop_table("job_requirements")
    op.drop_table("job_offer_fields")
    op.drop_table("job_offers")
    op.execute(
        "DELETE FROM evidence_spans WHERE evidence_source_id IN "
        "(SELECT id FROM evidence_sources WHERE source_type = 'job_offer')"
    )
    op.execute("DELETE FROM evidence_sources WHERE source_type = 'job_offer'")
    op.drop_constraint(
        op.f("ck_evidence_sources_source_document_type"),
        "evidence_sources",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_evidence_sources_source_document_type"),
        "evidence_sources",
        "(source_type = 'document' AND source_document_id IS NOT NULL) OR "
        "(source_type = 'user_statement' AND source_document_id IS NULL)",
    )
