"""Tests for typed application configuration."""

import pytest
from pydantic import ValidationError

from jobhunter.config import Settings


def test_settings_have_safe_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JOBHUNTER_DATABASE_URL", raising=False)
    settings = Settings(_env_file=None)

    assert settings.app_name == "JobHunter AI"
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert str(settings.database_url) == (
        "postgresql+psycopg://jobhunter:jobhunter@127.0.0.1:5432/jobhunter"
    )
    assert str(settings.document_storage_path).replace("\\", "/") == "storage/documents"
    assert settings.document_max_size_bytes == 10 * 1024 * 1024


def test_settings_reject_unknown_environment() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="staging", _env_file=None)


def test_settings_reject_non_postgres_database() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite:///jobhunter.db", _env_file=None)


def test_settings_reject_non_positive_document_limit() -> None:
    with pytest.raises(ValidationError):
        Settings(document_max_size_bytes=0, _env_file=None)
