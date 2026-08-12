"""Application health endpoint."""

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

from jobhunter import __version__
from jobhunter.config import Settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Public health status returned by the API."""

    model_config = ConfigDict(frozen=True)

    status: Literal["ok"]
    service: str
    environment: str
    version: str


@router.get("/health", summary="Check API health")
def health(request: Request) -> HealthResponse:
    """Report that the API process is available."""

    settings: Settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.environment,
        version=__version__,
    )
