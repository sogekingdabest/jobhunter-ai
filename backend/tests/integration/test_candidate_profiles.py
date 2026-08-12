"""End-to-end PostgreSQL API tests for manual candidate profiles."""

import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi import status
from fastapi.testclient import TestClient

from jobhunter.config import Settings
from jobhunter.main import create_app

pytestmark = pytest.mark.integration


def get_test_database_url() -> str:
    url = os.getenv("JOBHUNTER_TEST_DATABASE_URL")
    if url is None:
        pytest.skip("JOBHUNTER_TEST_DATABASE_URL is not configured")
    return url


def migrate(database_url: str) -> None:
    backend_root = Path(__file__).parents[2]
    configuration = Config(backend_root / "alembic.ini")
    configuration.attributes["database_url"] = database_url
    command.upgrade(configuration, "head")


def payload() -> dict[str, object]:
    return {
        "full_name": "Ada Lovelace",
        "headline": "Backend Engineer",
        "summary": "Builds reliable services.",
        "email": "ada@example.test",
        "phone": "+34 600 000 000",
        "location": "Madrid",
        "remote_preference": "hybrid",
        "preferred_roles": ["Backend Engineer"],
        "preferred_locations": ["Madrid", "Remote EU"],
        "work_experiences": [
            {
                "employer": "Analytical Engines",
                "title": "Software Engineer",
                "start_date": "2023-01-01",
                "description": "Designed APIs.",
            }
        ],
        "education": [
            {
                "institution": "University of London",
                "qualification": "BSc",
                "field_of_study": "Mathematics",
            }
        ],
        "projects": [
            {
                "name": "JobHunter AI",
                "description": "Explainable job matching.",
                "url": "https://example.test/project",
            }
        ],
        "competencies": [
            {"name": "Python", "category": "programming_language", "months_experience": 36}
        ],
        "languages": [{"language": "English", "level": "fluent"}],
    }


def test_candidate_profile_crud_and_provenance() -> None:
    database_url = get_test_database_url()
    migrate(database_url)
    app = create_app(Settings(environment="test", database_url=database_url, _env_file=None))

    with TestClient(app) as client:
        created_response = client.post("/candidate-profiles", json=payload())
        assert created_response.status_code == status.HTTP_201_CREATED
        created = created_response.json()
        profile_id = created["id"]
        source_id = created["evidence_source_id"]
        assert created["work_experiences"][0]["evidence_source_id"] == source_id

        fetched = client.get(f"/candidate-profiles/{profile_id}")
        assert fetched.status_code == status.HTTP_200_OK
        assert fetched.json() == created

        replacement = payload()
        replacement["headline"] = "Senior Backend Engineer"
        replacement["projects"] = [{"id": created["projects"][0]["id"], "name": "JobHunter AI"}]
        replaced_response = client.put(f"/candidate-profiles/{profile_id}", json=replacement)
        assert replaced_response.status_code == status.HTTP_200_OK
        replaced = replaced_response.json()
        assert replaced["headline"] == "Senior Backend Engineer"
        assert replaced["projects"][0]["id"] == created["projects"][0]["id"]
        assert replaced["evidence_source_id"] != source_id
        assert replaced["created_at"] == created["created_at"]

        assert (
            client.delete(f"/candidate-profiles/{profile_id}").status_code
            == status.HTTP_204_NO_CONTENT
        )
        assert (
            client.get(f"/candidate-profiles/{profile_id}").status_code == status.HTTP_404_NOT_FOUND
        )
        assert (
            client.put(f"/candidate-profiles/{profile_id}", json=payload()).status_code
            == status.HTTP_404_NOT_FOUND
        )
        assert (
            client.delete(f"/candidate-profiles/{profile_id}").status_code
            == status.HTTP_404_NOT_FOUND
        )


def test_candidate_profile_rejects_invalid_domain_fact() -> None:
    database_url = get_test_database_url()
    migrate(database_url)
    app = create_app(Settings(environment="test", database_url=database_url, _env_file=None))
    invalid = payload()
    invalid["preferred_roles"] = ["Backend", " backend "]

    with TestClient(app) as client:
        response = client.post("/candidate-profiles", json=invalid)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"] == "duplicate_preferred_role"


def test_candidate_profile_replace_rejects_invalid_domain_fact() -> None:
    database_url = get_test_database_url()
    migrate(database_url)
    app = create_app(Settings(environment="test", database_url=database_url, _env_file=None))
    with TestClient(app) as client:
        created = client.post("/candidate-profiles", json=payload()).json()
        invalid = payload()
        duplicate_id = str(uuid4())
        invalid["projects"] = [
            {"id": duplicate_id, "name": "One"},
            {"id": duplicate_id, "name": "Two"},
        ]
        response = client.put(f"/candidate-profiles/{created['id']}", json=invalid)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"] == "duplicate_entity_id"
    UUID(created["id"])
