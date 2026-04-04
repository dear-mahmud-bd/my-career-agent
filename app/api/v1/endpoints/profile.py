from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.profile import Profile
from app.models.skill import Skill
from app.models.job_preference import JobPreference
from app.core.security import check_auth
from app.services.llm import llm_router

router = APIRouter()
templates = Jinja2Templates(directory="app/ui/templates")


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not check_auth(request):
        return RedirectResponse(url="/login")

    profile = await db.scalar(select(Profile))
    skills_result = await db.execute(select(Skill))
    skills = skills_result.scalars().all()
    preferences = await db.scalar(select(JobPreference))
    llm_provider = await llm_router.get_active_provider()

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "active_page": "profile",
            "llm_provider": llm_provider,
            "profile": profile,
            "skills": skills,
            "preferences": preferences,
        },
    )


@router.post("/api/v1/profile/update")
async def update_profile(
    request: Request,
    full_name: str = Form(""),
    current_title: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    location: str = Form(""),
    summary: str = Form(""),
    linkedin_url: str = Form(""),
    github_url: str = Form(""),
    portfolio_url: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    if not check_auth(request):
        return RedirectResponse(url="/login")

    profile = await db.scalar(select(Profile))

    if not profile:
        profile = Profile()
        db.add(profile)

    profile.full_name = full_name
    profile.current_title = current_title
    profile.email = email
    profile.phone = phone
    profile.location = location
    profile.summary = summary
    profile.linkedin_url = linkedin_url
    profile.github_url = github_url
    profile.portfolio_url = portfolio_url

    await db.commit()
    return RedirectResponse(
        url="/profile?message=Profile+saved&message_type=success",
        status_code=303,
    )


@router.post("/api/v1/profile/skills/add")
async def add_skill(
    request: Request,
    name: str = Form(...),
    level: str = Form("intermediate"),
    category: str = Form("tool"),
    db: AsyncSession = Depends(get_db),
):
    if not check_auth(request):
        return RedirectResponse(url="/login")

    skill = Skill(
        name=name.strip(),
        level=level,
        category=category,
    )
    db.add(skill)
    await db.commit()

    return RedirectResponse(url="/profile", status_code=303)


@router.post("/api/v1/profile/skills/{skill_id}/delete")
async def delete_skill(
    skill_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not check_auth(request):
        return RedirectResponse(url="/login")

    skill = await db.get(Skill, skill_id)
    if skill:
        await db.delete(skill)
        await db.commit()

    return RedirectResponse(url="/profile", status_code=303)


@router.post("/api/v1/profile/preferences/update")
async def update_preferences(
    request: Request,
    work_type: str = Form("any"),
    location_type: str = Form("both"),
    preferred_country: str = Form(""),
    preferred_city: str = Form(""),
    job_titles: str = Form(""),
    experience_level: str = Form("mid"),
    min_salary: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    if not check_auth(request):
        return RedirectResponse(url="/login")

    preferences = await db.scalar(select(JobPreference))

    if not preferences:
        preferences = JobPreference()
        db.add(preferences)

    preferences.work_type = work_type
    preferences.location_type = location_type
    preferences.preferred_country = preferred_country
    preferences.preferred_city = preferred_city
    preferences.job_titles = job_titles
    preferences.experience_level = experience_level
    preferences.min_salary = int(min_salary) if min_salary else None

    await db.commit()
    return RedirectResponse(
        url="/profile?message=Preferences+saved&message_type=success",
        status_code=303,
    )