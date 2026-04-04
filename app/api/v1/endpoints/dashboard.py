from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.database import get_db
from app.models.job import Job, JobMatch
from app.models.skill import Skill
from app.models.notification import Notification
from app.core.security import check_auth
from app.services.matching.matcher import SkillMatcher
from app.services.llm import llm_router

router = APIRouter()
templates = Jinja2Templates(directory="app/ui/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not check_auth(request):
        return RedirectResponse(url="/login")

    # Stats
    total_jobs = await db.scalar(
        select(func.count(Job.id))
    ) or 0

    good_matches = await db.scalar(
        select(func.count(JobMatch.id)).where(
            JobMatch.match_score >= 65
        )
    ) or 0

    notifications_sent = await db.scalar(
        select(func.count(Notification.id)).where(
            Notification.is_sent == True
        )
    ) or 0

    total_skills = await db.scalar(
        select(func.count(Skill.id))
    ) or 0

    # Top matches
    matcher = SkillMatcher(db)
    top_matches = await matcher.get_top_matches(limit=5)

    # Recent notifications
    result = await db.execute(
        select(Notification)
        .order_by(Notification.created_at.desc())
        .limit(8)
    )
    recent_notifications = result.scalars().all()

    # Active LLM
    llm_provider = await llm_router.get_active_provider()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active_page": "dashboard",
            "llm_provider": llm_provider,
            "stats": {
                "total_jobs": total_jobs,
                "good_matches": good_matches,
                "notifications_sent": notifications_sent,
                "total_skills": total_skills,
                "threshold": 65,
            },
            "top_matches": top_matches,
            "recent_notifications": recent_notifications,
        },
    )