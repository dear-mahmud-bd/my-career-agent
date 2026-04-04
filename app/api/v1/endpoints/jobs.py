from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.database import get_db
from app.models.job import Job, JobMatch
from app.core.security import check_auth
from app.services.llm import llm_router
from app.workers.tasks import scrape_and_match_jobs

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


@router.post("/api/v1/jobs/trigger-scrape")
async def trigger_scrape(request: Request):
    if not check_auth(request):
        return RedirectResponse(url="/login")

    scrape_and_match_jobs.delay()

    return RedirectResponse(
        url="/dashboard?message=Job+scan+started&message_type=success",
        status_code=303,
    )