"""PostgreSQL/pgvector cache for versioned semantic embeddings."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.ai.domain.embeddings import EmbeddingModel, EmbeddingVector
from jobhunter.matching.domain.semantic import SemanticDocument, SemanticEmbedding
from jobhunter.matching.infrastructure.database.models import SemanticEmbeddingModel


class SqlAlchemySemanticEmbeddingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, document: SemanticDocument, model: EmbeddingModel
    ) -> SemanticEmbedding | None:
        statement = select(SemanticEmbeddingModel).where(
            SemanticEmbeddingModel.source_type == document.source_type,
            SemanticEmbeddingModel.source_id == document.source_id,
            SemanticEmbeddingModel.content_hash == document.content_hash,
            SemanticEmbeddingModel.provider == model.provider,
            SemanticEmbeddingModel.model == model.model,
            SemanticEmbeddingModel.revision == model.revision,
            SemanticEmbeddingModel.dimensions == model.dimensions,
            SemanticEmbeddingModel.candidate_profile_id == document.candidate_profile_id,
            SemanticEmbeddingModel.job_offer_id == document.job_offer_id,
        )
        stored = await self._session.scalar(statement)
        return None if stored is None else _to_domain(stored, document)

    async def add_many(
        self, embeddings: tuple[SemanticEmbedding, ...]
    ) -> tuple[SemanticEmbedding, ...]:
        self._session.add_all(_to_model(item) for item in embeddings)
        await self._session.commit()
        return embeddings


def _to_model(embedding: SemanticEmbedding) -> SemanticEmbeddingModel:
    document = embedding.document
    return SemanticEmbeddingModel(
        id=embedding.id,
        candidate_profile_id=document.candidate_profile_id,
        job_offer_id=document.job_offer_id,
        source_type=document.source_type,
        source_id=document.source_id,
        content_hash=document.content_hash,
        provider=embedding.model.provider,
        model=embedding.model.model,
        revision=embedding.model.revision,
        dimensions=embedding.model.dimensions,
        embedding=list(embedding.vector.values),
    )


def _to_domain(stored: SemanticEmbeddingModel, document: SemanticDocument) -> SemanticEmbedding:
    return SemanticEmbedding(
        stored.id,
        document,
        EmbeddingModel(stored.provider, stored.model, stored.revision, stored.dimensions),
        EmbeddingVector(tuple(float(value) for value in stored.embedding)),
    )
