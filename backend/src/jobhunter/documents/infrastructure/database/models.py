"""Relational models for source documents and evidence."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from jobhunter.documents.domain.entities import DocumentStatus, EvidenceSourceType
from jobhunter.documents.domain.media_types import DOCX_MEDIA_TYPE, PDF_MEDIA_TYPE, TEXT_MEDIA_TYPE
from jobhunter.infrastructure.database.base import Base


class SourceDocumentModel(Base):
    """Database representation of immutable document metadata."""

    __tablename__ = "source_documents"
    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="positive_size"),
        CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="sha256_format"),
        CheckConstraint(
            f"media_type IN ('{PDF_MEDIA_TYPE}', '{DOCX_MEDIA_TYPE}', '{TEXT_MEDIA_TYPE}')",
            name="supported_media_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'stored', 'processing', 'processed', 'failed')",
            name="supported_status",
        ),
        CheckConstraint(
            "(status = 'failed' AND failure_code IS NOT NULL) OR "
            "(status <> 'failed' AND failure_code IS NULL)",
            name="failure_code_status",
        ),
        Index("ix_source_documents_sha256", "sha256"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    media_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(
            DocumentStatus,
            native_enum=False,
            values_callable=lambda values: [item.value for item in values],
        )
    )
    parser_version: Mapped[str | None] = mapped_column(String(50))
    failure_code: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EvidenceSourceModel(Base):
    """Database representation of a document or explicit user statement."""

    __tablename__ = "evidence_sources"
    __table_args__ = (
        CheckConstraint(
            "(source_type = 'document' AND source_document_id IS NOT NULL) OR "
            "(source_type IN ('user_statement', 'job_offer') "
            "AND source_document_id IS NULL)",
            name="source_document_type",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    source_type: Mapped[EvidenceSourceType] = mapped_column(
        Enum(
            EvidenceSourceType,
            native_enum=False,
            values_callable=lambda values: [item.value for item in values],
        )
    )
    source_document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("source_documents.id", ondelete="RESTRICT"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvidenceSpanModel(Base):
    """Database representation of an exact supporting text span."""

    __tablename__ = "evidence_spans"
    __table_args__ = (
        CheckConstraint("length(quoted_text) > 0", name="quoted_text_present"),
        CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="sha256_format"),
        CheckConstraint(
            "(start_offset IS NULL AND end_offset IS NULL) OR "
            "(start_offset >= 0 AND end_offset > start_offset)",
            name="valid_offsets",
        ),
        CheckConstraint("page_number IS NULL OR page_number > 0", name="positive_page"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    evidence_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_sources.id", ondelete="CASCADE"), index=True
    )
    quoted_text: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    start_offset: Mapped[int | None]
    end_offset: Mapped[int | None]
    page_number: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
