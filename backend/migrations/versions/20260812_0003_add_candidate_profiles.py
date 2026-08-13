"""Add candidate profile aggregate.

Revision ID: 20260812_0003
Revises: 20260812_0002
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0003"
down_revision: str | None = "20260812_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _owned_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_profile_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_source_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"], ["candidate_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["evidence_source_id"], ["evidence_sources.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    ]


def _owned_indexes(table: str) -> None:
    op.create_index(f"ix_{table}_candidate_profile_id", table, ["candidate_profile_id"])
    op.create_index(f"ix_{table}_evidence_source_id", table, ["evidence_source_id"])


def upgrade() -> None:
    """Create the aggregate root and its owned entity tables."""

    op.create_table(
        "candidate_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evidence_source_id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("headline", sa.String(length=250), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column(
            "remote_preference",
            sa.Enum("onsite", "hybrid", "remote", "flexible", native_enum=False),
            nullable=True,
        ),
        sa.Column("preferred_roles", sa.JSON(), nullable=False),
        sa.Column("preferred_locations", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["evidence_source_id"], ["evidence_sources.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_candidate_profiles_evidence_source_id", "candidate_profiles", ["evidence_source_id"]
    )

    op.create_table(
        "candidate_work_experiences",
        *_owned_columns(),
        sa.Column("employer", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name=op.f("ck_candidate_work_experiences_valid_date_range"),
        ),
    )
    _owned_indexes("candidate_work_experiences")

    op.create_table(
        "candidate_education",
        *_owned_columns(),
        sa.Column("institution", sa.String(length=200), nullable=False),
        sa.Column("qualification", sa.String(length=200), nullable=False),
        sa.Column("field_of_study", sa.String(length=200), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name=op.f("ck_candidate_education_valid_date_range"),
        ),
    )
    _owned_indexes("candidate_education")

    op.create_table(
        "candidate_projects",
        *_owned_columns(),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=True),
    )
    _owned_indexes("candidate_projects")

    op.create_table(
        "candidate_competencies",
        *_owned_columns(),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "programming_language",
                "framework",
                "database",
                "cloud",
                "devops",
                "tool",
                "soft_skill",
                "other",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("months_experience", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "months_experience IS NULL OR months_experience >= 0",
            name=op.f("ck_candidate_competencies_non_negative_months_experience"),
        ),
    )
    _owned_indexes("candidate_competencies")

    op.create_table(
        "candidate_languages",
        *_owned_columns(),
        sa.Column("language", sa.String(length=100), nullable=False),
        sa.Column(
            "level",
            sa.Enum(
                "basic",
                "conversational",
                "professional",
                "fluent",
                "native",
                native_enum=False,
            ),
            nullable=False,
        ),
    )
    _owned_indexes("candidate_languages")


def downgrade() -> None:
    """Remove the candidate aggregate in dependency order."""

    op.drop_table("candidate_languages")
    op.drop_table("candidate_competencies")
    op.drop_table("candidate_projects")
    op.drop_table("candidate_education")
    op.drop_table("candidate_work_experiences")
    op.drop_table("candidate_profiles")
