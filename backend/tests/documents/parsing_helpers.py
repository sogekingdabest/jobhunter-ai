"""Builders for small, fictional document fixtures."""

from io import BytesIO
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from jobhunter.documents.domain.validation import DOCX_MAIN_CONTENT_TYPE


def pdf_bytes(*pages: str, encrypted: bool = False) -> bytes:
    """Build a deterministic text-layer PDF without storing a binary fixture."""

    writer = PdfWriter()
    for page_text in pages:
        page = writer.add_blank_page(width=595, height=842)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
        )
        instructions = ["BT /F1 12 Tf 72 780 Td"]
        for index, line in enumerate(page_text.splitlines()):
            if index:
                instructions.append("0 -18 Td")
            escaped_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            instructions.append(f"({escaped_line}) Tj")
        instructions.append("ET")
        stream = DecodedStreamObject()
        stream.set_data("\n".join(instructions).encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)

    if encrypted:
        writer.encrypt("fictional-password")
    target = BytesIO()
    writer.write(target)
    return target.getvalue()


def docx_bytes(*paragraphs: str, document_xml: bytes | None = None) -> bytes:
    """Build a minimal WordprocessingML container with fictional text."""

    if document_xml is None:
        body = "".join(
            f"<w:p><w:r><w:t>{escape(paragraph)}</w:t></w:r></w:p>" for paragraph in paragraphs
        )
        document_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{WORD_NAMESPACE}"><w:body>{body}</w:body></w:document>'
        ).encode()

    target = BytesIO()
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            b"<Types>" + DOCX_MAIN_CONTENT_TYPE + b"</Types>",
        )
        archive.writestr("word/document.xml", document_xml)
    return target.getvalue()


WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
