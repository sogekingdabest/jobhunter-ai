"""Bounded DOCX main-document XML parser."""

from io import BytesIO
from pathlib import PurePosixPath
from xml.etree.ElementTree import Element, ParseError
from zipfile import BadZipFile, LargeZipFile, ZipFile

from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import fromstring

from jobhunter.documents.domain.errors import InvalidDocumentError, NoExtractableTextError
from jobhunter.documents.domain.media_types import DOCX_MEDIA_TYPE
from jobhunter.documents.domain.parsing import ParsedDocument, build_parsed_document

PARSER_VERSION = "docx-v1"
WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
PARAGRAPH_TAG = f"{{{WORD_NAMESPACE}}}p"
TEXT_TAG = f"{{{WORD_NAMESPACE}}}t"
TAB_TAG = f"{{{WORD_NAMESPACE}}}tab"
BREAK_TAGS = frozenset((f"{{{WORD_NAMESPACE}}}br", f"{{{WORD_NAMESPACE}}}cr"))
MAX_ARCHIVE_MEMBERS = 1_024
MAX_TOTAL_UNCOMPRESSED_BYTES = 20 * 1024 * 1024
MAX_DOCUMENT_XML_BYTES = 5 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200
FORBIDDEN_XML_DECLARATIONS = (b"<!DOCTYPE", b"<!ENTITY")


class DocxDocumentParser:
    """Extract paragraphs from the bounded WordprocessingML main part."""

    media_type = DOCX_MEDIA_TYPE

    def parse(self, content: bytes) -> ParsedDocument:
        try:
            with ZipFile(BytesIO(content)) as archive:
                self._validate_archive(archive)
                document_xml = archive.read("word/document.xml")
        except (
            BadZipFile,
            LargeZipFile,
            KeyError,
            RuntimeError,
            NotImplementedError,
            OSError,
        ) as error:
            raise InvalidDocumentError from error

        upper_xml = document_xml.upper()
        if any(declaration in upper_xml for declaration in FORBIDDEN_XML_DECLARATIONS):
            raise InvalidDocumentError

        try:
            root = fromstring(document_xml)
        except (ParseError, DefusedXmlException) as error:
            raise InvalidDocumentError from error

        blocks = tuple(
            (self._paragraph_text(paragraph), None) for paragraph in root.iter(PARAGRAPH_TAG)
        )
        try:
            return build_parsed_document(blocks, parser_version=PARSER_VERSION)
        except ValueError as error:
            raise NoExtractableTextError from error

    @staticmethod
    def _validate_archive(archive: ZipFile) -> None:
        members = archive.infolist()
        if not members or len(members) > MAX_ARCHIVE_MEMBERS:
            raise InvalidDocumentError
        if sum(member.file_size for member in members) > MAX_TOTAL_UNCOMPRESSED_BYTES:
            raise InvalidDocumentError

        for member in members:
            path = PurePosixPath(member.filename)
            if (
                member.flag_bits & 1
                or "\\" in member.filename
                or path.is_absolute()
                or ".." in path.parts
            ):
                raise InvalidDocumentError
            if member.file_size and (
                member.compress_size == 0
                or member.file_size / member.compress_size > MAX_COMPRESSION_RATIO
            ):
                raise InvalidDocumentError

        try:
            document_info = archive.getinfo("word/document.xml")
        except KeyError as error:
            raise InvalidDocumentError from error
        if document_info.file_size > MAX_DOCUMENT_XML_BYTES:
            raise InvalidDocumentError

    @staticmethod
    def _paragraph_text(paragraph: Element) -> str:
        pieces: list[str] = []
        for element in paragraph.iter():
            if element.tag == TEXT_TAG and element.text:
                pieces.append(element.text)
            elif element.tag == TAB_TAG:
                pieces.append("\t")
            elif element.tag in BREAK_TAGS:
                pieces.append("\n")
        return "".join(pieces)
