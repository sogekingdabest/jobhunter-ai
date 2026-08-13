"""UTF-8 plain-text document parser."""

import re

from jobhunter.documents.domain.errors import InvalidDocumentError, NoExtractableTextError
from jobhunter.documents.domain.media_types import TEXT_MEDIA_TYPE
from jobhunter.documents.domain.parsing import ParsedDocument, build_parsed_document

PARSER_VERSION = "text-v1"
PARAGRAPH_SEPARATOR = re.compile(r"\n[ \t]*\n+")


class TextDocumentParser:
    """Parse UTF-8 text into paragraph spans."""

    media_type = TEXT_MEDIA_TYPE

    def parse(self, content: bytes) -> ParsedDocument:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise InvalidDocumentError from error
        if "\x00" in text:
            raise InvalidDocumentError

        normalized_newlines = text.replace("\r\n", "\n").replace("\r", "\n")
        blocks = tuple((block, None) for block in PARAGRAPH_SEPARATOR.split(normalized_newlines))
        try:
            return build_parsed_document(blocks, parser_version=PARSER_VERSION)
        except ValueError as error:
            raise NoExtractableTextError from error
