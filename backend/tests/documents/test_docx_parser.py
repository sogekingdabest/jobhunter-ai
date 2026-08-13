"""Tests for bounded WordprocessingML parsing."""

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from jobhunter.documents.domain.errors import InvalidDocumentError, NoExtractableTextError
from jobhunter.documents.infrastructure.parsing import docx as docx_module
from jobhunter.documents.infrastructure.parsing.docx import DocxDocumentParser
from tests.documents.parsing_helpers import WORD_NAMESPACE, docx_bytes

EXPECTED_SPANS = 2


def test_docx_parser_extracts_paragraphs_tabs_breaks_and_table_text() -> None:
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <w:document xmlns:w="{WORD_NAMESPACE}"><w:body>
      <w:p><w:r><w:t>Alex Example</w:t><w:tab/><w:t>Engineer</w:t>
      <w:br/><w:t>Madrid</w:t></w:r></w:p>
      <w:tbl><w:tr><w:tc><w:p><w:r><w:t>Python</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
    </w:body></w:document>""".encode()

    parsed = DocxDocumentParser().parse(docx_bytes(document_xml=xml))

    assert parsed.parser_version == "docx-v1"
    assert parsed.text == "Alex Example\tEngineer\nMadrid\n\nPython"
    assert len(parsed.spans) == EXPECTED_SPANS
    assert all(span.page_number is None for span in parsed.spans)


@pytest.mark.parametrize(
    "content",
    [
        b"not a zip",
        docx_bytes(document_xml=b"<broken>"),
        docx_bytes(document_xml=b"<!DOCTYPE x><document />"),
        docx_bytes(document_xml=b"<!ENTITY x 'value'><document />"),
    ],
)
def test_docx_parser_rejects_invalid_or_unsafe_xml(content: bytes) -> None:
    with pytest.raises(InvalidDocumentError):
        DocxDocumentParser().parse(content)


def test_docx_parser_rejects_document_without_text() -> None:
    with pytest.raises(NoExtractableTextError):
        DocxDocumentParser().parse(docx_bytes(" "))


def test_docx_parser_rejects_missing_main_part() -> None:
    target = BytesIO()
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", b"types")

    with pytest.raises(InvalidDocumentError):
        DocxDocumentParser().parse(target.getvalue())


def test_docx_parser_rejects_empty_archive() -> None:
    target = BytesIO()
    with ZipFile(target, "w"):
        pass

    with pytest.raises(InvalidDocumentError):
        DocxDocumentParser().parse(target.getvalue())


def test_docx_parser_enforces_archive_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    content = docx_bytes("Safe fictional text")

    monkeypatch.setattr(docx_module, "MAX_ARCHIVE_MEMBERS", 0)
    with pytest.raises(InvalidDocumentError):
        DocxDocumentParser().parse(content)

    monkeypatch.setattr(docx_module, "MAX_ARCHIVE_MEMBERS", 1_024)
    monkeypatch.setattr(docx_module, "MAX_TOTAL_UNCOMPRESSED_BYTES", 0)
    with pytest.raises(InvalidDocumentError):
        DocxDocumentParser().parse(content)

    monkeypatch.setattr(docx_module, "MAX_TOTAL_UNCOMPRESSED_BYTES", 20 * 1024 * 1024)
    monkeypatch.setattr(docx_module, "MAX_DOCUMENT_XML_BYTES", 0)
    with pytest.raises(InvalidDocumentError):
        DocxDocumentParser().parse(content)


@pytest.mark.parametrize(
    ("filename", "encrypted", "force_zero_compressed"),
    [
        ("../word/document.xml", False, False),
        ("/word/document.xml", False, False),
        ("word\\document.xml", False, False),
        ("word/document.xml", True, False),
        ("word/document.xml", False, True),
    ],
)
def test_docx_parser_rejects_unsafe_members(
    filename: str, encrypted: bool, force_zero_compressed: bool
) -> None:
    content = docx_bytes("Safe fictional text")
    with ZipFile(BytesIO(content)) as archive:
        members = archive.infolist()
        document = archive.getinfo("word/document.xml")
        document.filename = filename
        if encrypted:
            document.flag_bits |= 1
        if force_zero_compressed:
            document.compress_size = 0
        with pytest.raises(InvalidDocumentError):
            DocxDocumentParser._validate_archive(archive)
        assert members


def test_docx_parser_rejects_extreme_compression_ratio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = docx_bytes("Safe fictional text")
    monkeypatch.setattr(docx_module, "MAX_COMPRESSION_RATIO", 0)

    with pytest.raises(InvalidDocumentError):
        DocxDocumentParser().parse(content)
