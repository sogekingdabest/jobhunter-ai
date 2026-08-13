"""Text-layer PDF parser with bounded output."""

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from jobhunter.documents.domain.errors import (
    EncryptedDocumentError,
    InvalidDocumentError,
    NoExtractableTextError,
)
from jobhunter.documents.domain.media_types import PDF_MEDIA_TYPE
from jobhunter.documents.domain.parsing import ParsedDocument, build_parsed_document

PARSER_VERSION = "pypdf-v1"
MAX_PDF_PAGES = 500
MAX_EXTRACTED_TEXT_CHARS = 2_000_000


class PdfDocumentParser:
    """Extract each PDF text layer as a page-addressable span."""

    media_type = PDF_MEDIA_TYPE

    def parse(self, content: bytes) -> ParsedDocument:
        try:
            reader = PdfReader(BytesIO(content), strict=True)
            encrypted = reader.is_encrypted
            pages = tuple(reader.pages) if not encrypted else ()
        except (PdfReadError, ValueError, TypeError, KeyError, OSError, OverflowError) as error:
            raise InvalidDocumentError from error
        if encrypted:
            raise EncryptedDocumentError
        if len(pages) > MAX_PDF_PAGES:
            raise InvalidDocumentError

        blocks: list[tuple[str, int | None]] = []
        extracted_chars = 0
        oversized_output = False
        try:
            for page_number, page in enumerate(pages, start=1):
                text = page.extract_text() or ""
                extracted_chars += len(text)
                if extracted_chars > MAX_EXTRACTED_TEXT_CHARS:
                    oversized_output = True
                    break
                blocks.append((text, page_number))
        except (PdfReadError, ValueError, TypeError, KeyError, OSError, OverflowError) as error:
            raise InvalidDocumentError from error
        if oversized_output:
            raise InvalidDocumentError

        try:
            return build_parsed_document(tuple(blocks), parser_version=PARSER_VERSION)
        except ValueError as error:
            raise NoExtractableTextError from error
