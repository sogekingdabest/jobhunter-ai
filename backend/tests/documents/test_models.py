"""Tests for document provenance relational metadata."""

from jobhunter.documents.infrastructure.database.models import (
    EvidenceSourceModel,
    EvidenceSpanModel,
    SourceDocumentModel,
)
from jobhunter.infrastructure.database.base import Base


def test_document_models_are_registered_in_shared_metadata() -> None:
    assert Base.metadata.tables.keys() >= {
        SourceDocumentModel.__tablename__,
        EvidenceSourceModel.__tablename__,
        EvidenceSpanModel.__tablename__,
    }


def test_document_foreign_keys_define_expected_deletion_policy() -> None:
    source_foreign_key = next(iter(EvidenceSourceModel.__table__.foreign_keys))
    span_foreign_key = next(iter(EvidenceSpanModel.__table__.foreign_keys))

    assert source_foreign_key.ondelete == "RESTRICT"
    assert span_foreign_key.ondelete == "CASCADE"
