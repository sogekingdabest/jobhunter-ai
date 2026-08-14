"""Tests for the API health endpoint."""

from fastapi.testclient import TestClient
from starlette import status

from jobhunter.config import Settings
from jobhunter.main import create_app

REQUEST_ID_LENGTH = 36


def test_health_returns_service_metadata() -> None:
    app = create_app(
        Settings(
            app_name="JobHunter AI Test",
            environment="test",
            _env_file=None,
        )
    )

    with TestClient(app) as client:
        response = client.get("/health", headers={"x-request-id": "portfolio-check-1"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "ok",
        "service": "JobHunter AI Test",
        "environment": "test",
        "version": "0.1.0",
    }
    assert response.headers["x-request-id"] == "portfolio-check-1"
    assert response.headers["server-timing"].startswith("app;dur=")


def test_invalid_request_id_is_replaced() -> None:
    app = create_app(Settings(environment="test", _env_file=None))

    with TestClient(app) as client:
        response = client.get("/health", headers={"x-request-id": "contains spaces"})

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["x-request-id"] != "contains spaces"
    assert len(response.headers["x-request-id"]) == REQUEST_ID_LENGTH


def test_openapi_exposes_health_operation() -> None:
    app = create_app(Settings(environment="test", _env_file=None))

    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()

    assert "/health" in schema["paths"]
