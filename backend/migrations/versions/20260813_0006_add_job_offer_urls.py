"""Add verified URL provenance to job offers.

Revision ID: 20260813_0006
Revises: 20260813_0005
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_0006"
down_revision: str | None = "20260813_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store requested and canonical URLs with a source-consistency invariant."""

    op.add_column("job_offers", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column("job_offers", sa.Column("canonical_url", sa.Text(), nullable=True))
    op.create_check_constraint(
        op.f("ck_job_offers_source_urls_consistent"),
        "job_offers",
        "(source = 'manual' AND source_url IS NULL AND canonical_url IS NULL) OR "
        "(source = 'url' AND length(source_url) > 0 AND length(canonical_url) > 0)",
    )


def downgrade() -> None:
    """Remove URL provenance without affecting existing manual offers."""

    op.drop_constraint(
        op.f("ck_job_offers_source_urls_consistent"),
        "job_offers",
        type_="check",
    )
    op.drop_column("job_offers", "canonical_url")
    op.drop_column("job_offers", "source_url")
