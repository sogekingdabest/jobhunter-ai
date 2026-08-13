"""Contract implemented by deterministic document parsers."""

from typing import Protocol

from jobhunter.documents.domain.parsing import ParsedDocument


class DocumentParser(Protocol):  # pragma: no cover - structural typing contract
    """Extract normalized text from one trusted document format."""

    media_type: str

    def parse(self, content: bytes) -> ParsedDocument:
        """Parse validated document bytes or raise a domain document error."""
