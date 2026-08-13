"""Tests for normalized parsed-document domain results."""

from collections.abc import Callable

import pytest

from jobhunter.documents.domain.parsing import (
    ParsedDocument,
    ParsedTextSpan,
    build_parsed_document,
)


def test_build_parsed_document_normalizes_blocks_and_offsets() -> None:
    parsed = build_parsed_document(
        ((" First\r\nline ", None), ("  ", None), ("Second", 2)),
        parser_version="fixture-v1",
    )

    assert parsed.text == "First\nline\n\nSecond"
    assert parsed.spans == (ParsedTextSpan(0, 10), ParsedTextSpan(12, 18, 2))
    assert parsed.text[parsed.spans[1].start_offset : parsed.spans[1].end_offset] == "Second"


@pytest.mark.parametrize(
    ("span", "expected"),
    [
        (lambda: ParsedTextSpan(-1, 1), "invalid_parsed_span"),
        (lambda: ParsedTextSpan(1, 1), "invalid_parsed_span"),
        (lambda: ParsedTextSpan(0, 1, 0), "invalid_page_number"),
    ],
)
def test_parsed_span_rejects_invalid_coordinates(span: Callable[[], object], expected: str) -> None:
    with pytest.raises(ValueError, match=expected):
        span()


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        (lambda: ParsedDocument("", (ParsedTextSpan(0, 1),), "v1"), "missing_parsed_text"),
        (lambda: ParsedDocument("text", (), "v1"), "missing_parsed_spans"),
        (lambda: ParsedDocument("text", (ParsedTextSpan(0, 4),), ""), "missing_parser_version"),
        (
            lambda: ParsedDocument("text", (ParsedTextSpan(0, 4), ParsedTextSpan(3, 4)), "v1"),
            "invalid_parsed_span_order",
        ),
        (
            lambda: ParsedDocument("text", (ParsedTextSpan(0, 5),), "v1"),
            "invalid_parsed_span_order",
        ),
        (lambda: ParsedDocument(" x", (ParsedTextSpan(0, 1),), "v1"), "empty_parsed_span"),
    ],
)
def test_parsed_document_rejects_invalid_results(
    result: Callable[[], object], expected: str
) -> None:
    with pytest.raises(ValueError, match=expected):
        result()


def test_build_parsed_document_rejects_empty_blocks() -> None:
    with pytest.raises(ValueError, match="missing_parsed_text"):
        build_parsed_document(((" \n ", None),), parser_version="v1")
