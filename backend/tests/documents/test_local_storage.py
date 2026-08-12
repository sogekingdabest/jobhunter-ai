"""Tests for root-confined local document storage."""

from pathlib import Path
from unittest.mock import patch
from uuid import UUID

import pytest

from jobhunter.documents.domain.errors import InvalidStorageKeyError
from jobhunter.documents.infrastructure.storage.local import (
    LocalDocumentStorage,
    build_document_storage_key,
)
from jobhunter.documents.ports.storage import DocumentStorage


def test_build_document_storage_key_is_opaque_and_sharded() -> None:
    document_id = UUID("12345678-1234-5678-1234-567812345678")

    assert build_document_storage_key(document_id) == (
        "documents/12/12345678123456781234567812345678"
    )
    assert DocumentStorage is not None


@pytest.mark.asyncio
async def test_local_storage_write_read_delete_cycle(tmp_path: Path) -> None:
    storage = LocalDocumentStorage(tmp_path)
    key = "documents/ab/abcdef"

    await storage.write(key, b"private CV")

    assert await storage.read(key) == b"private CV"
    with pytest.raises(FileExistsError):
        await storage.write(key, b"replacement")

    await storage.delete(key)
    await storage.delete(key)
    assert not (tmp_path / "documents" / "ab" / "abcdef").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "storage_key",
    ["../outside", "/absolute", "documents\\outside", ".", ""],
)
async def test_local_storage_rejects_unsafe_keys(tmp_path: Path, storage_key: str) -> None:
    storage = LocalDocumentStorage(tmp_path)

    with pytest.raises(InvalidStorageKeyError):
        await storage.write(storage_key, b"private CV")


@pytest.mark.asyncio
async def test_local_storage_rejects_resolved_path_outside_root(tmp_path: Path) -> None:
    storage = LocalDocumentStorage(tmp_path)
    outside = tmp_path.parent / "outside"

    with (
        patch.object(Path, "resolve", return_value=outside),
        pytest.raises(InvalidStorageKeyError),
    ):
        await storage.write("documents/ab/abcdef", b"private CV")
