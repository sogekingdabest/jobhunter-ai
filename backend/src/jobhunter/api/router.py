"""Root API router."""

from fastapi import APIRouter

from jobhunter.api.routes.health import router as health_router
from jobhunter.candidate.api.fact_extraction_routes import router as fact_extraction_router
from jobhunter.candidate.api.routes import router as candidate_router
from jobhunter.jobs.api.routes import router as job_offer_router
from jobhunter.matching.api.routes import router as matching_router
from jobhunter.resume.api.routes import router as resume_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(candidate_router)
api_router.include_router(fact_extraction_router)
api_router.include_router(job_offer_router)
api_router.include_router(matching_router)
api_router.include_router(resume_router)
