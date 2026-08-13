"""Shared candidate-domain validation helpers."""

from collections.abc import Iterable
from uuid import UUID


def require_text(value: str, field: str) -> None:
    """Reject empty or whitespace-only domain text."""

    if not value.strip():
        raise ValueError(f"missing_{field}")


def ensure_unique_ids(ids: Iterable[UUID]) -> None:
    """Ensure nested aggregate entities have stable, unique identities."""

    values = tuple(ids)
    if len(values) != len(set(values)):
        raise ValueError("duplicate_entity_id")


def ensure_unique_text(values: Iterable[str], field: str) -> None:
    """Ensure case-insensitive uniqueness for normalized user lists."""

    normalized = tuple(value.strip().casefold() for value in values)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"duplicate_{field}")
    if any(not value for value in normalized):
        raise ValueError(f"missing_{field}")
