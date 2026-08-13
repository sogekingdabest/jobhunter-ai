"""add semantic matching

Revision ID: 20260813_0008
Revises: 20260813_0007
Create Date: 2026-08-13 19:40:49.386416
"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op

revision: str = "20260813_0008"
down_revision: str | None = "20260813_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply the migration."""

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "semantic_embeddings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_profile_id", sa.Uuid(), nullable=True),
        sa.Column("job_offer_id", sa.Uuid(), nullable=True),
        sa.Column(
            "source_type",
            sa.Enum(
                "candidate_summary",
                "candidate_work_experience",
                "candidate_project",
                "job_description",
                "job_responsibility",
                name="semanticsourcetype",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("revision", sa.String(length=100), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.vector.VECTOR(), nullable=False),
        sa.CheckConstraint(
            "(candidate_profile_id IS NOT NULL AND job_offer_id IS NULL) OR "
            "(candidate_profile_id IS NULL AND job_offer_id IS NOT NULL)",
            name=op.f("ck_semantic_embeddings_one_embedding_scope"),
        ),
        sa.CheckConstraint(
            "dimensions > 0 AND dimensions <= 2000",
            name=op.f("ck_semantic_embeddings_dimensions_range"),
        ),
        sa.CheckConstraint(
            "vector_dims(embedding) = dimensions",
            name=op.f("ck_semantic_embeddings_embedding_dimensions_match"),
        ),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_semantic_embeddings_candidate_profile_id_candidate_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_offer_id"],
            ["job_offers.id"],
            name=op.f("fk_semantic_embeddings_job_offer_id_job_offers"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_semantic_embeddings")),
    )
    op.create_index(
        op.f("ix_semantic_embeddings_candidate_profile_id"),
        "semantic_embeddings",
        ["candidate_profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_semantic_embeddings_job_offer_id"),
        "semantic_embeddings",
        ["job_offer_id"],
        unique=False,
    )
    op.create_index(
        "uq_semantic_embeddings_candidate_cache_key",
        "semantic_embeddings",
        [
            "candidate_profile_id",
            "source_type",
            "source_id",
            "content_hash",
            "provider",
            "model",
            "revision",
        ],
        unique=True,
        postgresql_where=sa.text("candidate_profile_id IS NOT NULL"),
    )
    op.create_index(
        "uq_semantic_embeddings_job_cache_key",
        "semantic_embeddings",
        [
            "job_offer_id",
            "source_type",
            "source_id",
            "content_hash",
            "provider",
            "model",
            "revision",
        ],
        unique=True,
        postgresql_where=sa.text("job_offer_id IS NOT NULL"),
    )
    op.create_table(
        "match_semantic_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "job_source_type",
            sa.Enum(
                "candidate_summary",
                "candidate_work_experience",
                "candidate_project",
                "job_description",
                "job_responsibility",
                name="semanticsourcetype",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("job_source_id", sa.Uuid(), nullable=False),
        sa.Column(
            "candidate_source_type",
            sa.Enum(
                "candidate_summary",
                "candidate_work_experience",
                "candidate_project",
                "job_description",
                "job_responsibility",
                name="semanticsourcetype",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("candidate_source_id", sa.Uuid(), nullable=False),
        sa.Column("similarity", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "similarity >= 0 AND similarity <= 1",
            name=op.f("ck_match_semantic_evidence_similarity_range"),
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["match_assessments.id"],
            name=op.f("fk_match_semantic_evidence_assessment_id_match_assessments"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_match_semantic_evidence")),
        sa.UniqueConstraint(
            "assessment_id", "position", name="uq_match_semantic_evidence_assessment_position"
        ),
    )
    op.create_index(
        op.f("ix_match_semantic_evidence_assessment_id"),
        "match_semantic_evidence",
        ["assessment_id"],
        unique=False,
    )
    op.add_column("match_assessments", sa.Column("structured_score", sa.Float(), nullable=True))
    op.execute("UPDATE match_assessments SET structured_score = score")
    op.alter_column("match_assessments", "structured_score", nullable=False)
    op.add_column("match_assessments", sa.Column("semantic_score", sa.Float(), nullable=True))
    op.add_column(
        "match_assessments",
        sa.Column("semantic_weight", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "match_assessments", sa.Column("embedding_provider", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "match_assessments", sa.Column("embedding_model", sa.String(length=200), nullable=True)
    )
    op.add_column(
        "match_assessments", sa.Column("embedding_revision", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "match_assessments", sa.Column("embedding_dimensions", sa.Integer(), nullable=True)
    )
    op.create_check_constraint(
        op.f("ck_match_assessments_structured_score_range"),
        "match_assessments",
        "structured_score >= 0 AND structured_score <= 100",
    )
    op.create_check_constraint(
        op.f("ck_match_assessments_semantic_score_range"),
        "match_assessments",
        "semantic_score IS NULL OR (semantic_score >= 0 AND semantic_score <= 100)",
    )
    op.create_check_constraint(
        op.f("ck_match_assessments_semantic_weight_range"),
        "match_assessments",
        "semantic_weight >= 0 AND semantic_weight < 1",
    )
    op.alter_column("match_assessments", "semantic_weight", server_default=None)


def downgrade() -> None:
    """Revert the migration."""

    op.drop_constraint(
        op.f("ck_match_assessments_semantic_weight_range"),
        "match_assessments",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_match_assessments_semantic_score_range"),
        "match_assessments",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_match_assessments_structured_score_range"),
        "match_assessments",
        type_="check",
    )
    op.drop_column("match_assessments", "embedding_dimensions")
    op.drop_column("match_assessments", "embedding_revision")
    op.drop_column("match_assessments", "embedding_model")
    op.drop_column("match_assessments", "embedding_provider")
    op.drop_column("match_assessments", "semantic_weight")
    op.drop_column("match_assessments", "semantic_score")
    op.drop_column("match_assessments", "structured_score")
    op.drop_index(
        op.f("ix_match_semantic_evidence_assessment_id"), table_name="match_semantic_evidence"
    )
    op.drop_table("match_semantic_evidence")
    op.drop_index(
        "uq_semantic_embeddings_job_cache_key",
        table_name="semantic_embeddings",
        postgresql_where=sa.text("job_offer_id IS NOT NULL"),
    )
    op.drop_index(
        "uq_semantic_embeddings_candidate_cache_key",
        table_name="semantic_embeddings",
        postgresql_where=sa.text("candidate_profile_id IS NOT NULL"),
    )
    op.drop_index(op.f("ix_semantic_embeddings_job_offer_id"), table_name="semantic_embeddings")
    op.drop_index(
        op.f("ix_semantic_embeddings_candidate_profile_id"), table_name="semantic_embeddings"
    )
    op.drop_table("semantic_embeddings")
