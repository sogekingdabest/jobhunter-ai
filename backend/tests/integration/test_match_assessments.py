"""End-to-end PostgreSQL API tests for structured match assessments."""

import asyncio
from uuid import UUID, uuid4

from fastapi import status
from fastapi.testclient import TestClient

from jobhunter.ai.domain.embeddings import EmbeddingModel, EmbeddingVector
from jobhunter.candidate.infrastructure.database.repository import (
    SqlAlchemyCandidateProfileRepository,
)
from jobhunter.config import Settings
from jobhunter.infrastructure.database.session import Database
from jobhunter.jobs.application.normalization import ManualJobOfferService
from jobhunter.jobs.infrastructure.database.repository import SqlAlchemyJobOfferRepository
from jobhunter.main import create_app
from jobhunter.matching.application.service import MatchingService
from jobhunter.matching.domain.semantic import (
    SemanticDocument,
    SemanticEmbedding,
    SemanticSourceType,
)
from jobhunter.matching.infrastructure.database.embedding_repository import (
    SqlAlchemySemanticEmbeddingRepository,
)
from jobhunter.matching.infrastructure.database.repository import (
    SqlAlchemyMatchAssessmentRepository,
)
from tests.candidate.factories import make_profile
from tests.integration.test_candidate_profiles import (
    get_test_database_url,
    migrate,
)
from tests.integration.test_candidate_profiles import (
    payload as candidate_payload,
)
from tests.integration.test_job_offers import payload as job_payload
from tests.jobs.factories import JOB_TEXT, make_normalization

EXPECTED_STRUCTURED_SCORE = 61.11


def test_match_repository_round_trips_assessment() -> None:
    database_url = get_test_database_url()
    migrate(database_url)
    asyncio.run(_exercise_match_repository(database_url))


async def _exercise_match_repository(database_url: str) -> None:
    database = Database(database_url)
    try:
        async with database.session() as session:
            candidates = SqlAlchemyCandidateProfileRepository(session)
            jobs = SqlAlchemyJobOfferRepository(session)
            assessments = SqlAlchemyMatchAssessmentRepository(session)
            candidate = await candidates.add(make_profile())
            offer = await ManualJobOfferService(jobs).import_normalized(
                f"{JOB_TEXT}\nRepository reference: {uuid4()}", make_normalization()
            )
            service = MatchingService(candidates, jobs, assessments)

            created = await service.assess(candidate.id, offer.id)

            assert await assessments.get(created.id) == created
            assert await assessments.get(UUID(int=0)) is None

            document = SemanticDocument(
                SemanticSourceType.CANDIDATE_SUMMARY,
                candidate.id,
                "Backend engineer building reliable services",
                candidate_profile_id=candidate.id,
            )
            model = EmbeddingModel("google", "embeddinggemma-300M", "2025-09", 3)
            embedding = SemanticEmbedding(
                uuid4(), document, model, EmbeddingVector((1.0, 0.5, 0.25))
            )
            embedding_repository = SqlAlchemySemanticEmbeddingRepository(session)
            assert await embedding_repository.get(document, model) is None
            assert await embedding_repository.add_many((embedding,)) == (embedding,)
            assert await embedding_repository.get(document, model) == embedding
    finally:
        await database.dispose()


def test_structured_match_is_persisted_and_explained() -> None:
    database_url = get_test_database_url()
    migrate(database_url)
    app = create_app(Settings(environment="test", database_url=database_url, _env_file=None))

    with TestClient(app) as client:
        candidate = client.post("/candidate-profiles", json=candidate_payload()).json()
        offer = client.post("/job-offers/manual", json=job_payload()).json()
        response = client.post(
            "/match-assessments",
            json={"candidate_profile_id": candidate["id"], "job_offer_id": offer["id"]},
        )
        assert response.status_code == status.HTTP_201_CREATED
        assessment = response.json()
        assert assessment["policy_version"] == "structured-v1"
        assert assessment["score"] == EXPECTED_STRUCTURED_SCORE
        assert assessment["recommendation"] == "blocked"
        assert {gate["status"] for gate in assessment["gates"]} == {"passed", "failed"}
        assert assessment["dimensions"][0]["evidence"][0]["candidate_fact_ids"]
        assert assessment["dimensions"][0]["evidence"][0]["candidate_values"] == ["Python"]
        assert assessment["dimensions"][0]["evidence"][0]["job_value"] == "Python"

        fetched = client.get(f"/match-assessments/{assessment['id']}")
        assert fetched.status_code == status.HTTP_200_OK
        assert fetched.json() == assessment

        assert (
            client.delete(f"/candidate-profiles/{candidate['id']}").status_code
            == status.HTTP_204_NO_CONTENT
        )
        assert (
            client.get(f"/match-assessments/{assessment['id']}").status_code
            == status.HTTP_404_NOT_FOUND
        )

        missing = client.get("/match-assessments/00000000-0000-0000-0000-000000000000")
        assert missing.status_code == status.HTTP_404_NOT_FOUND


def test_structured_match_returns_missing_inputs() -> None:
    database_url = get_test_database_url()
    migrate(database_url)
    app = create_app(Settings(environment="test", database_url=database_url, _env_file=None))
    missing_id = "00000000-0000-0000-0000-000000000000"

    with TestClient(app) as client:
        candidate = client.post("/candidate-profiles", json=candidate_payload()).json()
        missing_candidate = client.post(
            "/match-assessments",
            json={"candidate_profile_id": missing_id, "job_offer_id": missing_id},
        )
        missing_offer = client.post(
            "/match-assessments",
            json={"candidate_profile_id": candidate["id"], "job_offer_id": missing_id},
        )

    assert missing_candidate.json()["detail"] == "candidate_profile_not_found"
    assert missing_offer.json()["detail"] == "job_offer_not_found"
