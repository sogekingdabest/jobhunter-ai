"""SQLAlchemy persistence for grounded candidate-fact extraction."""

from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from jobhunter.candidate.domain.facts import CandidateFactExtraction, CandidateFactProposal
from jobhunter.candidate.infrastructure.database.models import (
    CandidateFactExtractionModel,
    CandidateFactProposalModel,
)
from jobhunter.candidate.ports.fact_extraction_repository import (
    CandidateFactExtractionConflictError,
)
from jobhunter.documents.domain.entities import EvidenceSource, EvidenceSpan
from jobhunter.documents.infrastructure.database.models import (
    EvidenceSourceModel,
    EvidenceSpanModel,
)


class SqlAlchemyCandidateFactExtractionRepository:
    """Persist evidence and extraction review state transactionally."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        extraction: CandidateFactExtraction,
        evidence_source: EvidenceSource,
        evidence_spans: tuple[EvidenceSpan, ...],
    ) -> CandidateFactExtraction:
        self._session.add(
            EvidenceSourceModel(
                id=evidence_source.id,
                source_type=evidence_source.source_type,
                source_document_id=evidence_source.source_document_id,
                created_at=evidence_source.created_at,
            )
        )
        await self._session.flush()
        self._session.add_all(
            [
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
            ]
        )
        await self._session.flush()
        self._session.add(_to_model(extraction))
        await self._session.commit()
        return await self._required(extraction.id)

    async def get(self, extraction_id: UUID) -> CandidateFactExtraction | None:
        model = await self._load(extraction_id)
        return None if model is None else _to_domain(model)

    async def replace(self, extraction: CandidateFactExtraction) -> CandidateFactExtraction | None:
        model = await self._load(extraction.id, for_update=True)
        if model is None:
            return None
        if model.revision != extraction.revision - 1:
            raise CandidateFactExtractionConflictError
        model.status = extraction.status
        model.revision = extraction.revision
        model.completed_at = extraction.completed_at
        decisions = {proposal.id: proposal for proposal in extraction.proposals}
        for proposal_model in model.proposals:
            proposal = decisions[proposal_model.id]
            proposal_model.review_status = proposal.review_status
            proposal_model.reviewed_at = proposal.reviewed_at
        await self._session.commit()
        return await self._required(extraction.id)

    async def _load(
        self, extraction_id: UUID, *, for_update: bool = False
    ) -> CandidateFactExtractionModel | None:
        statement = (
            select(CandidateFactExtractionModel)
            .where(CandidateFactExtractionModel.id == extraction_id)
            .options(
                selectinload(CandidateFactExtractionModel.proposals).options(
                    joinedload(CandidateFactProposalModel.evidence_span)
                )
            )
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(CandidateFactExtractionModel | None, await self._session.scalar(statement))

    async def _required(self, extraction_id: UUID) -> CandidateFactExtraction:
        stored = await self.get(extraction_id)
        if stored is None:  # pragma: no cover - protected by the transaction above
            raise RuntimeError("candidate_fact_extraction_not_persisted")
        return stored


def _to_model(extraction: CandidateFactExtraction) -> CandidateFactExtractionModel:
    return CandidateFactExtractionModel(
        id=extraction.id,
        source_document_id=extraction.source_document_id,
        evidence_source_id=extraction.evidence_source_id,
        contract_version=extraction.contract_version,
        provider=extraction.provider,
        model=extraction.model,
        warnings=list(extraction.warnings),
        status=extraction.status,
        revision=extraction.revision,
        created_at=extraction.created_at,
        completed_at=extraction.completed_at,
        proposals=[
            CandidateFactProposalModel(
                id=proposal.id,
                extraction_id=extraction.id,
                evidence_span_id=proposal.evidence_span_id,
                position=position,
                fact_type=proposal.fact_type,
                value=proposal.value,
                confidence=proposal.confidence,
                review_status=proposal.review_status,
                reviewed_at=proposal.reviewed_at,
            )
            for position, proposal in enumerate(extraction.proposals)
        ],
    )


def _to_domain(model: CandidateFactExtractionModel) -> CandidateFactExtraction:
    return CandidateFactExtraction(
        id=model.id,
        source_document_id=model.source_document_id,
        evidence_source_id=model.evidence_source_id,
        contract_version=model.contract_version,
        provider=model.provider,
        model=model.model,
        warnings=tuple(model.warnings),
        status=model.status,
        revision=model.revision,
        created_at=model.created_at,
        completed_at=model.completed_at,
        proposals=tuple(
            CandidateFactProposal(
                id=proposal.id,
                extraction_id=model.id,
                evidence_span_id=proposal.evidence_span_id,
                evidence_quote=proposal.evidence_span.quoted_text,
                start_offset=cast(int, proposal.evidence_span.start_offset),
                end_offset=cast(int, proposal.evidence_span.end_offset),
                page_number=proposal.evidence_span.page_number,
                fact_type=proposal.fact_type,
                value=proposal.value,
                confidence=proposal.confidence,
                review_status=proposal.review_status,
                reviewed_at=proposal.reviewed_at,
            )
            for proposal in model.proposals
        ),
    )
