from fastapi import APIRouter
from app.api.v1.endpoints import (
    dashboard,
    profile,
    jobs,
    sources,
    resume,
)

router = APIRouter()

router.include_router(dashboard.router)
router.include_router(profile.router)
router.include_router(jobs.router)
router.include_router(sources.router)
router.include_router(resume.router)