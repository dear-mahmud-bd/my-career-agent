from datetime import datetime
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.database import get_db
from app.models.job import Job, JobMatch
from app.core.security import check_auth
from app.services.llm import llm_router
from app.core.logger import logger

router = APIRouter()
templates = Jinja2Templates(directory="app/ui/templates")


@router.get("/jobs", response_class=HTMLResponse)
async def jobs_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not check_auth(request):
        return RedirectResponse(url="/login")

    result = await db.execute(
        select(Job, JobMatch)
        .join(JobMatch, Job.id == JobMatch.job_id)
        .where(Job.is_active == True)
        .order_by(desc(JobMatch.match_score))
        .limit(50)
    )

    jobs = []
    for job, match in result.all():
        jobs.append({
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": job.url,
            "work_type": job.work_type or "unknown",
            "location_type": job.location_type or "unknown",
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "match_score": match.match_score,
            "match_reason": match.match_reason,
            "matched_skills": match.matched_skills,
            "missing_skills": match.missing_skills,
        })

    llm_provider = await llm_router.get_active_provider()

    return templates.TemplateResponse(
        "jobs.html",
        {
            "request": request,
            "active_page": "jobs",
            "llm_provider": llm_provider,
            "jobs": jobs,
        },
    )


@router.get("/api/v1/jobs/scan-status")
async def scan_status(request: Request):
    if not check_auth(request):
        return JSONResponse(
            {"error": "unauthorized"}, status_code=401
        )
    from app.core.scan_manager import scan_manager
    return JSONResponse(scan_manager.get_status())


@router.post("/api/v1/jobs/trigger-scrape")
async def trigger_scrape(request: Request):
    if not check_auth(request):
        return JSONResponse(
            {"error": "unauthorized"}, status_code=401
        )

    from app.core.scan_manager import scan_manager
    import asyncio

    if scan_manager.is_scanning:
        return JSONResponse({
            "success": False,
            "message": "Scan already in progress"
        })

    # Run single scan immediately in background
    asyncio.create_task(scan_manager.run_once())

    return JSONResponse({
        "success": True,
        "message": "Scan started"
    })


@router.post("/api/v1/jobs/scan/start")
async def start_continuous_scan(request: Request):
    """Start the continuous scan loop."""
    if not check_auth(request):
        return JSONResponse(
            {"error": "unauthorized"}, status_code=401
        )

    from app.core.scan_manager import scan_manager

    if scan_manager.is_running:
        return JSONResponse({
            "success": False,
            "message": "Scan loop already running"
        })

    scan_manager.start()
    return JSONResponse({
        "success": True,
        "message": "Continuous scan started"
    })


@router.post("/api/v1/jobs/scan/stop")
async def stop_continuous_scan(request: Request):
    """Stop the continuous scan loop."""
    if not check_auth(request):
        return JSONResponse(
            {"error": "unauthorized"}, status_code=401
        )

    from app.core.scan_manager import scan_manager
    scan_manager.stop()

    return JSONResponse({
        "success": True,
        "message": "Scan loop stopped"
    })