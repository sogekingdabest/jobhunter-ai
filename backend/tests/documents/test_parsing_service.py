"""Tests for parsing validation, dispatch, and default composition."""

from pathlib import Path

import pytest

from jobhunter.documents.application.parsing import DocumentParsingService
from jobhunter.documents.domain.errors import (
    DocumentTypeMismatchError,
    UnsupportedDocumentTypeError,
)
from jobhunter.documents.domain.media_types import PDF_MEDIA_TYPE, TEXT_MEDIA_TYPE
from jobhunter.documents.domain.parsing import ParsedDocument, build_parsed_document
from jobhunter.documents.infrastructure.parsing import create_document_parsing_service
from tests.documents.parsing_helpers import docx_bytes, pdf_bytes

FIXTURE = Path(__file__).parents[1] / "fixtures" / "documents" / "fictional_cv.txt"


class FakeParser:
    """Test parser for application dispatch."""

    media_type = TEXT_MEDIA_TYPE

    def parse(self, content: bytes) -> ParsedDocument:
        return build_parsed_document(((content.decode(), None),), parser_version="fake-v1")


def test_parsing_service_validates_then_dispatches() -> None:
    service = DocumentParsingService((FakeParser(),), max_size_bytes=1024)

    parsed = service.parse(b"Fictional CV", declared_media_type=TEXT_MEDIA_TYPE)

    assert parsed.parser_version == "fake-v1"


def test_parsing_service_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError, match="missing_document_parsers"):
        DocumentParsingService((), max_size_bytes=1)
    with pytest.raises(ValueError, match="invalid_max_size_bytes"):
        DocumentParsingService((FakeParser(),), max_size_bytes=0)
    with pytest.raises(ValueError, match="duplicate_document_parser"):
        DocumentParsingService((FakeParser(), FakeParser()), max_size_bytes=1)


def test_parsing_service_rejects_type_mismatch_and_missing_adapter() -> None:
    service = DocumentParsingService((FakeParser(),), max_size_bytes=1024)

    with pytest.raises(DocumentTypeMismatchError):
        service.parse(b"Fictional CV", declared_media_type=PDF_MEDIA_TYPE)
    with pytest.raises(UnsupportedDocumentTypeError):
        service.parse(pdf_bytes("Fictional CV"))


@pytest.mark.parametrize(
    ("content", "expected_version"),
    [
        (FIXTURE.read_bytes(), "text-v1"),
        (pdf_bytes("Alex Example"), "pypdf-v1"),
        (docx_bytes("Alex Example"), "docx-v1"),
    ],
)
def test_default_parsing_service_supports_every_validated_format(
    content: bytes, expected_version: str
) -> None:
    parsed = create_document_parsing_service(max_size_bytes=1024 * 1024).parse(content)

    assert parsed.parser_version == expected_version
