"""SQLAlchemy implementation of the job offer repository port."""

from typing import cast
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from jobhunter.documents.domain.entities import EvidenceSource, EvidenceSpan
from jobhunter.documents.infrastructure.database.models import (
    EvidenceSourceModel,
    EvidenceSpanModel,
)
from jobhunter.jobs.domain.offers import JobOffer, JobOfferField, JobRequirement
from jobhunter.jobs.infrastructure.database.models import (
    JobOfferFieldModel,
    JobOfferModel,
    JobRequirementModel,
)
from jobhunter.jobs.ports.repository import JobOfferRepositoryDuplicateError

FINGERPRINT_CONSTRAINT = "uq_job_offers_content_fingerprint"


class SqlAlchemyJobOfferRepository:
    """Persist each offer, its normalized facts, and evidence atomically."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        offer: JobOffer,
        evidence_source: EvidenceSource,
        evidence_spans: tuple[EvidenceSpan, ...],
    ) -> JobOffer:
        self._session.add(
            EvidenceSourceModel(
                id=evidence_source.id,
                source_type=evidence_source.source_type,
                source_document_id=evidence_source.source_document_id,
                created_at=evidence_source.created_at,
            )
        )
        self._session.add_all(
            EvidenceSpanModel(
                id=span.id,
                evidence_source_id=span.evidence_source_id,
                quoted_text=span.quoted_text,
                sha256=span.sha256,
                start_offset=span.start_offset,
                end_offset=span.end_offset,
                page_number=span.page_number,
                created_at=span.created_at,
            )
            for span in evidence_spans
        )
        self._session.add(_to_model(offer))
        try:
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if constraint == FINGERPRINT_CONSTRAINT:
                raise JobOfferRepositoryDuplicateError from error
            raise  # pragma: no cover - an unrelated database invariant failed
        return await self._required(offer.id)

    async def get(self, offer_id: UUID) -> JobOffer | None:
        model = await self._session.scalar(self._statement().where(JobOfferModel.id == offer_id))
        return None if model is None else _to_domain(model)

    async def get_by_fingerprint(self, fingerprint: str) -> JobOffer | None:
        model = await self._session.scalar(
            self._statement().where(JobOfferModel.content_fingerprint == fingerprint)
        )
        return None if model is None else _to_domain(model)

    def _statement(self) -> Select[tuple[JobOfferModel]]:
        return select(JobOfferModel).options(
            selectinload(JobOfferModel.fields).joinedload(JobOfferFieldModel.evidence_span),
            selectinload(JobOfferModel.requirements).joinedload(JobRequirementModel.evidence_span),
        )

    async def _required(self, offer_id: UUID) -> JobOffer:
        offer = await self.get(offer_id)
        if offer is None:  # pragma: no cover - protected by the transaction above
            raise RuntimeError("job_offer_not_persisted")
        return offer


def _to_model(offer: JobOffer) -> JobOfferModel:
    return JobOfferModel(
        id=offer.id,
        evidence_source_id=offer.evidence_source_id,
        source=offer.source,
        raw_text=offer.raw_text,
        content_fingerprint=offer.content_fingerprint,
        normalization_version=offer.normalization_version,
        warnings=list(offer.warnings),
        discovered_at=offer.discovered_at,
        fields=[
            JobOfferFieldModel(
                id=field.id,
                job_offer_id=offer.id,
                evidence_span_id=field.evidence_span_id,
                position=position,
                name=field.name,
                value=field.value,
                confidence=field.confidence,
            )
            for position, field in enumerate(offer.fields)
        ],
        requirements=[
            JobRequirementModel(
                id=requirement.id,
                job_offer_id=offer.id,
                evidence_span_id=requirement.evidence_span_id,
                position=position,
                requirement_type=requirement.requirement_type,
                priority=requirement.priority,
                normalized_value=requirement.normalized_value,
                confidence=requirement.confidence,
            )
            for position, requirement in enumerate(offer.requirements)
        ],
    )


def _to_domain(model: JobOfferModel) -> JobOffer:
    return JobOffer(
        id=model.id,
        evidence_source_id=model.evidence_source_id,
        source=model.source,
        raw_text=model.raw_text,
        content_fingerprint=model.content_fingerprint,
        normalization_version=model.normalization_version,
        fields=tuple(
            JobOfferField(
                id=field.id,
                job_offer_id=model.id,
                evidence_span_id=field.evidence_span_id,
                name=field.name,
                value=field.value,
                evidence_quote=field.evidence_span.quoted_text,
                start_offset=cast(int, field.evidence_span.start_offset),
                end_offset=cast(int, field.evidence_span.end_offset),
                confidence=field.confidence,
            )
            for field in model.fields
        ),
        requirements=tuple(
            JobRequirement(
                id=requirement.id,
                job_offer_id=model.id,
                evidence_span_id=requirement.evidence_span_id,
                requirement_type=requirement.requirement_type,
                priority=requirement.priority,
                normalized_value=requirement.normalized_value,
                original_text=requirement.evidence_span.quoted_text,
                start_offset=cast(int, requirement.evidence_span.start_offset),
                end_offset=cast(int, requirement.evidence_span.end_offset),
                confidence=requirement.confidence,
            )
            for requirement in model.requirements
        ),
        warnings=tuple(model.warnings),
        discovered_at=model.discovered_at,
    )
