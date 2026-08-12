"""Storage contract for immutable source document bytes."""

from typing import Protocol


class DocumentStorage(Protocol):  # pragma: no cover - structural typing contract
    """Persist source documents without exposing filesystem concepts to the domain."""

    async def write(self, storage_key: str, content: bytes) -> None:
        """Store bytes at an opaque key, replacing no existing document."""

    async def read(self, storage_key: str) -> bytes:
        """Read bytes previously stored at an opaque key."""

    async def delete(self, storage_key: str) -> None:
        """Delete bytes if they exist."""
