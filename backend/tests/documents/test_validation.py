"""Tests for deterministic source document validation."""

from hashlib import sha256
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from jobhunter.documents.domain.errors import (
    DocumentTooLargeError,
    DocumentTypeMismatchError,
    EmptyDocumentError,
    UnsupportedDocumentTypeError,
)
from jobhunter.documents.domain.media_types import (
    DOCX_MEDIA_TYPE,
    PDF_MEDIA_TYPE,
    TEXT_MEDIA_TYPE,
)
from jobhunter.documents.domain.validation import (
    DOCX_MAIN_CONTENT_TYPE,
    MAX_CONTENT_TYPES_BYTES,
    detect_media_type,
    validate_document,
)


def docx_bytes(*, include_document: bool = True, content_types: bytes | None = None) -> bytes:
    target = BytesIO()
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            content_types or b"<Types>" + DOCX_MAIN_CONTENT_TYPE + b"</Types>",
        )
        if include_document:
            archive.writestr("word/document.xml", b"<document />")
    return target.getvalue()


@pytest.mark.parametrize(
    ("content", "media_type"),
    [
        (b"%PDF-1.7\n%%EOF", PDF_MEDIA_TYPE),
        (b"Curriculum vitae", TEXT_MEDIA_TYPE),
        (b"\xef\xbb\xbfCurriculum vitae", TEXT_MEDIA_TYPE),
    ],
)
def test_validate_document_derives_trusted_metadata(content: bytes, media_type: str) -> None:
    result = validate_document(content, max_size_bytes=1024, declared_media_type=media_type)

    assert result.media_type == media_type
    assert result.size_bytes == len(content)
    assert result.sha256 == sha256(content).hexdigest()


def test_detect_media_type_validates_docx_container() -> None:
    assert detect_media_type(docx_bytes()) == DOCX_MEDIA_TYPE


def test_validate_document_rejects_empty_and_oversized_content() -> None:
    with pytest.raises(EmptyDocumentError):
        validate_document(b"", max_size_bytes=1)
    with pytest.raises(DocumentTooLargeError, match="1-byte"):
        validate_document(b"CV", max_size_bytes=1)


def test_validate_document_rejects_declared_type_mismatch() -> None:
    with pytest.raises(DocumentTypeMismatchError):
        validate_document(
            b"plain text",
            max_size_bytes=1024,
            declared_media_type=PDF_MEDIA_TYPE,
        )


@pytest.mark.parametrize(
    "content",
    [
        b"\x00binary",
        b"\xff\xfeinvalid utf8",
        b" \n\t ",
        b"PK\x00invalid zip",
        docx_bytes(include_document=False),
        docx_bytes(content_types=b"<Types>not a Word document</Types>"),
        docx_bytes(content_types=b"x" * (MAX_CONTENT_TYPES_BYTES + 1)),
    ],
)
def test_detect_media_type_rejects_unsupported_content(content: bytes) -> None:
    with pytest.raises(UnsupportedDocumentTypeError):
        detect_media_type(content)
