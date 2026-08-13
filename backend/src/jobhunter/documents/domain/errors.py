"""Errors raised while validating and storing source documents."""


class DocumentError(Exception):
    """Base error for document operations."""


class EmptyDocumentError(DocumentError):
    """Raised when a source document has no content."""

    def __init__(self) -> None:
        super().__init__("document content is empty")


class DocumentTooLargeError(DocumentError):
    """Raised when a source document exceeds the configured byte limit."""

    def __init__(self, max_size_bytes: int) -> None:
        super().__init__(f"document exceeds the {max_size_bytes}-byte limit")


class UnsupportedDocumentTypeError(DocumentError):
    """Raised when content is not a supported document type."""

    def __init__(self) -> None:
        super().__init__("document content is not PDF, DOCX, or UTF-8 text")


class DocumentTypeMismatchError(DocumentError):
    """Raised when a declared media type does not match the content."""

    def __init__(self) -> None:
        super().__init__("declared media type does not match document content")


class InvalidStorageKeyError(DocumentError):
    """Raised when a storage key could escape the configured storage root."""

    def __init__(self) -> None:
        super().__init__("storage key must remain below the configured root")


class InvalidDocumentError(DocumentError):
    """Raised when a recognized document is malformed or unsafe to parse."""

    def __init__(self) -> None:
        super().__init__("document structure is invalid or exceeds parser safety limits")


class EncryptedDocumentError(DocumentError):
    """Raised when an encrypted document cannot be parsed without credentials."""

    def __init__(self) -> None:
        super().__init__("encrypted documents are not supported")


class NoExtractableTextError(DocumentError):
    """Raised when a valid document contains no machine-readable text."""

    def __init__(self) -> None:
        super().__init__("document contains no extractable text")
