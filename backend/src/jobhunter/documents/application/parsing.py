"""Use case for validated, deterministic document parsing."""

from collections.abc import Iterable

from jobhunter.documents.domain.errors import UnsupportedDocumentTypeError
from jobhunter.documents.domain.parsing import ParsedDocument
from jobhunter.documents.domain.validation import validate_document
from jobhunter.documents.ports.parser import DocumentParser


class DocumentParsingService:
    """Validate document bytes and dispatch to a format-specific parser."""

    def __init__(self, parsers: Iterable[DocumentParser], *, max_size_bytes: int) -> None:
        configured_parsers = tuple(parsers)
        self._parsers = {parser.media_type: parser for parser in configured_parsers}
        if not self._parsers:
            raise ValueError("missing_document_parsers")
        if len(self._parsers) != len(configured_parsers):
            raise ValueError("duplicate_document_parser")
        if max_size_bytes <= 0:
            raise ValueError("invalid_max_size_bytes")
        self._max_size_bytes = max_size_bytes

    def parse(self, content: bytes, *, declared_media_type: str | None = None) -> ParsedDocument:
        """Validate bytes before extracting normalized text and spans."""

        validated = validate_document(
            content,
            max_size_bytes=self._max_size_bytes,
            declared_media_type=declared_media_type,
        )
        parser = self._parsers.get(validated.media_type)
        if parser is None:
            raise UnsupportedDocumentTypeError
        return parser.parse(content)
