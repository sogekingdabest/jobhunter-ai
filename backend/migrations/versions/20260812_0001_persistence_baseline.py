"""Establish the persistence migration baseline.

Revision ID: 20260812_0001
Revises:
Create Date: 2026-08-12 00:00:00
"""

from collections.abc import Sequence

revision: str = "20260812_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply the initial empty schema baseline."""


def downgrade() -> None:
    """Return to the state before persistence was initialized."""
