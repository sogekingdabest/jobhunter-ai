"""Filesystem-backed document storage with opaque, root-confined keys."""

import asyncio
import os
from pathlib import Path, PurePosixPath
from uuid import UUID, uuid4

from jobhunter.documents.domain.errors import InvalidStorageKeyError


def build_document_storage_key(document_id: UUID) -> str:
    """Build an opaque, sharded key without retaining a user filename."""

    identifier = document_id.hex
    return f"documents/{identifier[:2]}/{identifier}"


class LocalDocumentStorage:
    """Store immutable files below one configured local root."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    async def write(self, storage_key: str, content: bytes) -> None:
        """Write content atomically and never replace an existing document."""

        await asyncio.to_thread(self._write, storage_key, content)

    async def read(self, storage_key: str) -> bytes:
        """Read one stored document."""

        path = self._resolve(storage_key)
        return await asyncio.to_thread(path.read_bytes)

    async def delete(self, storage_key: str) -> None:
        """Delete one stored document when present."""

        await asyncio.to_thread(self._resolve(storage_key).unlink, missing_ok=True)

    def _write(self, storage_key: str, content: bytes) -> None:
        target = self._resolve(storage_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.{uuid4().hex}.tmp")

        try:
            with temporary.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)

    def _resolve(self, storage_key: str) -> Path:
        if "\\" in storage_key:
            raise InvalidStorageKeyError

        key = PurePosixPath(storage_key)
        if key.is_absolute() or not key.parts or ".." in key.parts:
            raise InvalidStorageKeyError

        candidate = self.root.joinpath(*key.parts).resolve()
        if self.root not in candidate.parents:
            raise InvalidStorageKeyError
        return candidate
