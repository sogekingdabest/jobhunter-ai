"""FastAPI application entry point."""

from fastapi import FastAPI

from jobhunter import __version__
from jobhunter.api.router import api_router
from jobhunter.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    resolved_settings = settings or get_settings()
    application = FastAPI(
        title=resolved_settings.app_name,
        version=__version__,
        description="Explainable and provenance-aware job matching API.",
    )
    application.state.settings = resolved_settings
    application.include_router(api_router)
    return application


app = create_app()
