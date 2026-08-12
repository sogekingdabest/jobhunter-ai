"""Deterministic document inspection independent of user-supplied filenames."""

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from zipfile import BadZipFile, ZipFile

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

DOCX_MAIN_CONTENT_TYPE = (
    b"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
)
MAX_CONTENT_TYPES_BYTES = 64 * 1024


@dataclass(frozen=True, slots=True)
class ValidatedDocument:
    """Trusted metadata derived from document bytes."""

    media_type: str
    size_bytes: int
    sha256: str


def validate_document(
    content: bytes,
    *,
    max_size_bytes: int,
    declared_media_type: str | None = None,
) -> ValidatedDocument:
    """Validate size and content type, then calculate immutable metadata."""

    if not content:
        raise EmptyDocumentError
    if len(content) > max_size_bytes:
        raise DocumentTooLargeError(max_size_bytes)

    media_type = detect_media_type(content)
    if declared_media_type is not None and declared_media_type != media_type:
        raise DocumentTypeMismatchError

    return ValidatedDocument(
        media_type=media_type,
        size_bytes=len(content),
        sha256=sha256(content).hexdigest(),
    )


def detect_media_type(content: bytes) -> str:
    """Recognize the supported formats using signatures and container structure."""

    if content.startswith(b"%PDF-"):
        return PDF_MEDIA_TYPE
    if _is_docx(content):
        return DOCX_MEDIA_TYPE
    if _is_utf8_text(content):
        return TEXT_MEDIA_TYPE
    raise UnsupportedDocumentTypeError


def _is_docx(content: bytes) -> bool:
    if not content.startswith(b"PK"):
        return False
    try:
        with ZipFile(BytesIO(content)) as archive:
            names = set(archive.namelist())
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                return False
            content_types = archive.getinfo("[Content_Types].xml")
            if content_types.file_size > MAX_CONTENT_TYPES_BYTES:
                return False
            return DOCX_MAIN_CONTENT_TYPE in archive.read(content_types)
    except (BadZipFile, RuntimeError):
        return False


def _is_utf8_text(content: bytes) -> bool:
    if b"\x00" in content:
        return False
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return False
    return bool(decoded.strip())
