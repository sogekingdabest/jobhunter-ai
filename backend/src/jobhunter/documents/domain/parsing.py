"""Provider-neutral results produced by deterministic document parsing."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedTextSpan:
    """One non-empty block located inside normalized document text."""

    start_offset: int
    end_offset: int
    page_number: int | None = None

    def __post_init__(self) -> None:
        if self.start_offset < 0 or self.end_offset <= self.start_offset:
            raise ValueError("invalid_parsed_span")
        if self.page_number is not None and self.page_number <= 0:
            raise ValueError("invalid_page_number")


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """Normalized text and traceable blocks extracted without AI."""

    text: str
    spans: tuple[ParsedTextSpan, ...]
    parser_version: str

    def __post_init__(self) -> None:
        if not self.text:
            raise ValueError("missing_parsed_text")
        if not self.spans:
            raise ValueError("missing_parsed_spans")
        if not self.parser_version:
            raise ValueError("missing_parser_version")

        previous_end = 0
        for span in self.spans:
            if span.start_offset < previous_end or span.end_offset > len(self.text):
                raise ValueError("invalid_parsed_span_order")
            if not self.text[span.start_offset : span.end_offset].strip():
                raise ValueError("empty_parsed_span")
            previous_end = span.end_offset


def build_parsed_document(
    blocks: tuple[tuple[str, int | None], ...], *, parser_version: str
) -> ParsedDocument:
    """Normalize blocks and calculate offsets against one canonical text."""

    normalized_blocks_list: list[tuple[str, int | None]] = []
    for text, page_number in blocks:
        normalized = _normalize_block(text)
        if normalized:
            normalized_blocks_list.append((normalized, page_number))
    normalized_blocks = tuple(normalized_blocks_list)
    if not normalized_blocks:
        raise ValueError("missing_parsed_text")

    text_parts: list[str] = []
    spans: list[ParsedTextSpan] = []
    cursor = 0
    for text, page_number in normalized_blocks:
        if text_parts:
            text_parts.append("\n\n")
            cursor += 2
        start_offset = cursor
        text_parts.append(text)
        cursor += len(text)
        spans.append(ParsedTextSpan(start_offset, cursor, page_number))

    return ParsedDocument("".join(text_parts), tuple(spans), parser_version)


def _normalize_block(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    lines = tuple(line.strip() for line in normalized.split("\n"))
    return "\n".join(line for line in lines if line).strip()
