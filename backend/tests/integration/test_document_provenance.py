"""PostgreSQL integration tests for document provenance constraints."""

import asyncio
import os
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from jobhunter.documents.domain.entities import DocumentStatus, EvidenceSourceType
from jobhunter.documents.infrastructure.database.models import (
    EvidenceSourceModel,
    EvidenceSpanModel,
    SourceDocumentModel,
)
from jobhunter.infrastructure.database.session import Database

pytestmark = pytest.mark.integration


def get_test_database_url() -> str:
    url = os.getenv("JOBHUNTER_TEST_DATABASE_URL")
    if url is None:
        pytest.skip("JOBHUNTER_TEST_DATABASE_URL is not configured")
    return url


def alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).parents[2]
    configuration = Config(backend_root / "alembic.ini")
    configuration.attributes["database_url"] = database_url
    return configuration


def test_document_provenance_persists_and_enforces_constraints() -> None:
    database_url = get_test_database_url()
    command.upgrade(alembic_config(database_url), "head")

    asyncio.run(_exercise_document_provenance(database_url))


async def _exercise_document_provenance(database_url: str) -> None:
    database = Database(database_url)
    document_id = uuid4()
    source_id = uuid4()
    quoted_text = "Built secure APIs"

    try:
        async with database.session() as session:
            document = SourceDocumentModel(
                id=document_id,
                storage_key=f"documents/{document_id.hex[:2]}/{document_id.hex}",
                media_type="text/plain",
                size_bytes=17,
                sha256=sha256(b"fictional CV text").hexdigest(),
                status=DocumentStatus.STORED,
            )
            source = EvidenceSourceModel(
                id=source_id,
                source_type=EvidenceSourceType.DOCUMENT,
                source_document_id=document_id,
            )
            span = EvidenceSpanModel(
                id=uuid4(),
                evidence_source_id=source_id,
                quoted_text=quoted_text,
                sha256=sha256(quoted_text.encode()).hexdigest(),
                start_offset=0,
                end_offset=len(quoted_text),
                page_number=1,
            )
            session.add(document)
            await session.flush()
            session.add(source)
            await session.flush()
            session.add(span)
            await session.commit()

            stored = await session.get(SourceDocumentModel, document_id)
            assert stored is not None
            assert stored.status is DocumentStatus.STORED

        async with database.session() as session:
            invalid_source = EvidenceSourceModel(
                id=uuid4(),
                source_type=EvidenceSourceType.USER_STATEMENT,
                source_document_id=document_id,
            )
            session.add(invalid_source)
            with pytest.raises(IntegrityError):
                await session.flush()
            await session.rollback()

        async with database.session() as session:
            invalid_document_id = uuid4()
            invalid_document = SourceDocumentModel(
                id=invalid_document_id,
                storage_key=f"documents/{invalid_document_id.hex[:2]}/{invalid_document_id.hex}",
                media_type="text/plain",
                size_bytes=1,
                sha256="A" * 64,
                status=DocumentStatus.STORED,
            )
            session.add(invalid_document)
            with pytest.raises(IntegrityError):
                await session.flush()
            await session.rollback()

        async with database.session() as session:
            persisted_source = await session.get(EvidenceSourceModel, source_id)
            assert persisted_source is not None
            await session.delete(persisted_source)
            await session.commit()

            span_count = await session.scalar(
                select(func.count())
                .select_from(EvidenceSpanModel)
                .where(EvidenceSpanModel.evidence_source_id == source_id)
            )
            assert span_count == 0
    finally:
        await database.dispose()
