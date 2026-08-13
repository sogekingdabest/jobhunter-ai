"""Tests for document provenance domain invariants."""

from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

import pytest

from jobhunter.documents.domain.entities import (
    DocumentStatus,
    EvidenceSource,
    EvidenceSourceType,
    EvidenceSpan,
    SourceDocument,
)

NOW = datetime.now(UTC)
EVIDENCE_TEXT = "Evidence"
VALID_HASH = sha256(EVIDENCE_TEXT.encode()).hexdigest()


def source_document(**changes: object) -> SourceDocument:
    document = SourceDocument(
        id=uuid4(),
        storage_key="documents/ab/abcdef",
        media_type="text/plain",
        size_bytes=8,
        sha256=VALID_HASH,
        status=DocumentStatus.STORED,
        created_at=NOW,
        updated_at=NOW,
    )
    return replace(document, **changes)  # type: ignore[arg-type]


def evidence_span(**changes: object) -> EvidenceSpan:
    span = EvidenceSpan(
        id=uuid4(),
        evidence_source_id=uuid4(),
        quoted_text=EVIDENCE_TEXT,
        sha256=VALID_HASH,
        start_offset=0,
        end_offset=8,
        page_number=1,
        created_at=NOW,
    )
    return replace(span, **changes)  # type: ignore[arg-type]


def test_source_document_accepts_valid_failure_metadata() -> None:
    document = source_document(status=DocumentStatus.FAILED, failure_code="invalid_document")

    assert document.failure_code == "invalid_document"


@pytest.mark.parametrize(
    ("changes", "error_code"),
    [
        ({"size_bytes": 0}, "invalid_size"),
        ({"sha256": "not-a-hash"}, "invalid_sha256"),
        ({"sha256": "A" * 64}, "invalid_sha256"),
        ({"storage_key": ""}, "missing_storage_key"),
        ({"media_type": "image/png"}, "unsupported_media_type"),
        ({"status": DocumentStatus.FAILED}, "missing_failure_code"),
        ({"failure_code": "unexpected"}, "unexpected_failure_code"),
    ],
)
def test_source_document_rejects_invalid_metadata(
    changes: dict[str, object], error_code: str
) -> None:
    with pytest.raises(ValueError, match=error_code):
        source_document(**changes)


def test_evidence_source_enforces_origin_shape() -> None:
    document_id = uuid4()
    source = EvidenceSource(
        id=uuid4(),
        source_type=EvidenceSourceType.DOCUMENT,
        source_document_id=document_id,
        created_at=NOW,
    )
    statement = EvidenceSource(
        id=uuid4(),
        source_type=EvidenceSourceType.USER_STATEMENT,
        source_document_id=None,
        created_at=NOW,
    )
    external = EvidenceSource(
        id=uuid4(),
        source_type=EvidenceSourceType.JOB_OFFER,
        source_document_id=None,
        created_at=NOW,
    )

    assert source.source_document_id == document_id
    assert statement.source_document_id is None
    assert external.source_document_id is None


@pytest.mark.parametrize(
    ("source_type", "document_id", "error_code"),
    [
        (EvidenceSourceType.DOCUMENT, None, "missing_source_document"),
        (EvidenceSourceType.USER_STATEMENT, uuid4(), "unexpected_source_document"),
        (EvidenceSourceType.JOB_OFFER, uuid4(), "unexpected_source_document"),
    ],
)
def test_evidence_source_rejects_inconsistent_origin(
    source_type: EvidenceSourceType, document_id: UUID | None, error_code: str
) -> None:
    with pytest.raises(ValueError, match=error_code):
        EvidenceSource(
            id=uuid4(),
            source_type=source_type,
            source_document_id=document_id,
            created_at=NOW,
        )


def test_evidence_span_accepts_page_only_location() -> None:
    span = evidence_span(start_offset=None, end_offset=None)

    assert span.page_number == 1


@pytest.mark.parametrize(
    ("changes", "error_code"),
    [
        ({"quoted_text": ""}, "missing_evidence_text"),
        ({"sha256": "invalid"}, "invalid_sha256"),
        ({"sha256": sha256(b"other").hexdigest()}, "evidence_hash_mismatch"),
        ({"start_offset": None}, "incomplete_offsets"),
        ({"end_offset": None}, "incomplete_offsets"),
        ({"start_offset": -1}, "invalid_offsets"),
        ({"end_offset": 0}, "invalid_offsets"),
        ({"page_number": 0}, "invalid_page_number"),
    ],
)
def test_evidence_span_rejects_invalid_location(
    changes: dict[str, object], error_code: str
) -> None:
    with pytest.raises(ValueError, match=error_code):
        evidence_span(**changes)
