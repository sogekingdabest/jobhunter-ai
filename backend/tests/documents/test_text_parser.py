"""Tests for deterministic UTF-8 parsing."""

from pathlib import Path

import pytest

from jobhunter.documents.domain.errors import InvalidDocumentError, NoExtractableTextError
from jobhunter.documents.infrastructure.parsing.text import TextDocumentParser

FIXTURE = Path(__file__).parents[1] / "fixtures" / "documents" / "fictional_cv.txt"
EXPECTED_PARAGRAPHS = 3


def test_text_parser_extracts_fictional_fixture_with_offsets() -> None:
    parsed = TextDocumentParser().parse(FIXTURE.read_bytes())

    assert parsed.parser_version == "text-v1"
    assert len(parsed.spans) == EXPECTED_PARAGRAPHS
    assert parsed.text[parsed.spans[0].start_offset : parsed.spans[0].end_offset] == (
        "Alex Example\nBackend Engineer"
    )


def test_text_parser_normalizes_bom_and_windows_newlines() -> None:
    parsed = TextDocumentParser().parse(b"\xef\xbb\xbfFirst\r\nline\r\n\r\nSecond")

    assert parsed.text == "First\nline\n\nSecond"


@pytest.mark.parametrize("content", [b"\xff", b"text\x00binary"])
def test_text_parser_rejects_invalid_encoding(content: bytes) -> None:
    with pytest.raises(InvalidDocumentError):
        TextDocumentParser().parse(content)


def test_text_parser_rejects_whitespace_only_document() -> None:
    with pytest.raises(NoExtractableTextError):
        TextDocumentParser().parse(b" \r\n\t")
