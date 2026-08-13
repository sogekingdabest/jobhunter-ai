"""Pure domain entities for source documents and evidence."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from typing import cast
from uuid import UUID

from jobhunter.documents.domain.media_types import SUPPORTED_MEDIA_TYPES

SHA256_LENGTH = 64
LOWERCASE_HEXADECIMAL = frozenset("0123456789abcdef")


def _is_sha256(value: str) -> bool:
    return len(value) == SHA256_LENGTH and all(
        character in LOWERCASE_HEXADECIMAL for character in value
    )


class DocumentStatus(StrEnum):
    """Lifecycle of a source document without coupling it to a parser."""

    PENDING = "pending"
    STORED = "stored"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class EvidenceSourceType(StrEnum):
    """Allowed origins for facts used by generated content."""

    DOCUMENT = "document"
    USER_STATEMENT = "user_statement"
    JOB_OFFER = "job_offer"


@dataclass(frozen=True, slots=True)
class SourceDocument:
    """Metadata for one immutable, externally supplied document."""

    id: UUID
    storage_key: str
    media_type: str
    size_bytes: int
    sha256: str
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime
    parser_version: str | None = None
    failure_code: str | None = None

    def __post_init__(self) -> None:
        if self.size_bytes <= 0:
            raise ValueError("invalid_size")
        if not _is_sha256(self.sha256):
            raise ValueError("invalid_sha256")
        if not self.storage_key:
            raise ValueError("missing_storage_key")
        if self.media_type not in SUPPORTED_MEDIA_TYPES:
            raise ValueError("unsupported_media_type")
        if self.status is DocumentStatus.FAILED and self.failure_code is None:
            raise ValueError("missing_failure_code")
        if self.status is not DocumentStatus.FAILED and self.failure_code is not None:
            raise ValueError("unexpected_failure_code")


@dataclass(frozen=True, slots=True)
class EvidenceSource:
    """Origin that authorizes one or more candidate facts."""

    id: UUID
    source_type: EvidenceSourceType
    source_document_id: UUID | None
    created_at: datetime

    def __post_init__(self) -> None:
        has_document = self.source_document_id is not None
        if self.source_type is EvidenceSourceType.DOCUMENT and not has_document:
            raise ValueError("missing_source_document")
        if self.source_type is not EvidenceSourceType.DOCUMENT and has_document:
            raise ValueError("unexpected_source_document")


@dataclass(frozen=True, slots=True)
class EvidenceSpan:
    """Exact text range supporting a structured or generated fact."""

    id: UUID
    evidence_source_id: UUID
    quoted_text: str
    sha256: str
    start_offset: int | None
    end_offset: int | None
    page_number: int | None
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.quoted_text:
            raise ValueError("missing_evidence_text")
        if not _is_sha256(self.sha256):
            raise ValueError("invalid_sha256")
        if sha256(self.quoted_text.encode()).hexdigest() != self.sha256:
            raise ValueError("evidence_hash_mismatch")
        has_start = self.start_offset is not None
        has_end = self.end_offset is not None
        if has_start != has_end:
            raise ValueError("incomplete_offsets")
        if has_start and has_end:
            start_offset = cast(int, self.start_offset)
            end_offset = cast(int, self.end_offset)
            if start_offset < 0 or end_offset <= start_offset:
                raise ValueError("invalid_offsets")
        if self.page_number is not None and self.page_number <= 0:
            raise ValueError("invalid_page_number")
