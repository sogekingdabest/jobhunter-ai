"""Deterministic parsers for supported document formats."""

from jobhunter.documents.application.parsing import DocumentParsingService
from jobhunter.documents.infrastructure.parsing.docx import DocxDocumentParser
from jobhunter.documents.infrastructure.parsing.pdf import PdfDocumentParser
from jobhunter.documents.infrastructure.parsing.text import TextDocumentParser


def create_document_parsing_service(*, max_size_bytes: int) -> DocumentParsingService:
    """Compose every supported parser behind the application service."""

    return DocumentParsingService(
        (TextDocumentParser(), PdfDocumentParser(), DocxDocumentParser()),
        max_size_bytes=max_size_bytes,
    )


__all__ = ["create_document_parsing_service"]
