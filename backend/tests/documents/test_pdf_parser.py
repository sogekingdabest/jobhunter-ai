"""Tests for text-layer PDF parsing and safety limits."""

import pytest

from jobhunter.documents.domain.errors import (
    EncryptedDocumentError,
    InvalidDocumentError,
    NoExtractableTextError,
)
from jobhunter.documents.infrastructure.parsing import pdf as pdf_module
from jobhunter.documents.infrastructure.parsing.pdf import PdfDocumentParser
from tests.documents.parsing_helpers import pdf_bytes


def test_pdf_parser_extracts_page_addressable_spans() -> None:
    parsed = PdfDocumentParser().parse(
        pdf_bytes("Alex Example\nBackend Engineer", "Python SQL Docker")
    )

    assert parsed.parser_version == "pypdf-v1"
    assert parsed.text == "Alex Example\nBackend Engineer\n\nPython SQL Docker"
    assert [span.page_number for span in parsed.spans] == [1, 2]
    assert parsed.text[parsed.spans[1].start_offset : parsed.spans[1].end_offset] == (
        "Python SQL Docker"
    )


def test_pdf_parser_rejects_malformed_pdf() -> None:
    with pytest.raises(InvalidDocumentError):
        PdfDocumentParser().parse(b"%PDF-1.7\nmalformed")


def test_pdf_parser_rejects_encrypted_pdf() -> None:
    with pytest.raises(EncryptedDocumentError):
        PdfDocumentParser().parse(pdf_bytes("Secret", encrypted=True))


def test_pdf_parser_reports_pdf_without_text_layer() -> None:
    with pytest.raises(NoExtractableTextError):
        PdfDocumentParser().parse(pdf_bytes(""))


def test_pdf_parser_enforces_page_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf_module, "MAX_PDF_PAGES", 0)

    with pytest.raises(InvalidDocumentError):
        PdfDocumentParser().parse(pdf_bytes("Text"))


def test_pdf_parser_enforces_extracted_text_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf_module, "MAX_EXTRACTED_TEXT_CHARS", 1)

    with pytest.raises(InvalidDocumentError):
        PdfDocumentParser().parse(pdf_bytes("Too much text"))


def test_pdf_parser_translates_page_extraction_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenPage:
        def extract_text(self) -> str:
            raise ValueError

    class ReaderWithBrokenPage:
        is_encrypted = False
        pages = (BrokenPage(),)

    monkeypatch.setattr(pdf_module, "PdfReader", lambda *_args, **_kwargs: ReaderWithBrokenPage())

    with pytest.raises(InvalidDocumentError):
        PdfDocumentParser().parse(b"%PDF-fictional")
