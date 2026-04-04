from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.job_source import JobSource
from app.core.security import check_auth
from app.services.llm import llm_router

router = APIRouter()
templates = Jinja2Templates(directory="app/ui/templates")


@router.get("/sources", response_class=HTMLResponse)
async def sources_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not check_auth(request):
        return RedirectResponse(url="/login")

    result = await db.execute(
        select(JobSource).order_by(
            JobSource.created_at.desc()
        )
    )
    sources = result.scalars().all()
    llm_provider = await llm_router.get_active_provider()

    return templates.TemplateResponse(
        "sources.html",
        {
            "request": request,
            "active_page": "sources",
            "llm_provider": llm_provider,
            "sources": sources,
        },
    )


@router.post("/api/v1/sources/add")
async def add_source(
    request: Request,
    name: str = Form(...),
    url: str = Form(...),
    source_type: str = Form(...),
    company_name: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    if not check_auth(request):
        return RedirectResponse(url="/login")

    source = JobSource(
        name=name.strip(),
        url=url.strip(),
        source_type=source_type,
        company_name=company_name.strip() or None,
    )
    db.add(source)
    await db.commit()

    return RedirectResponse(url="/sources", status_code=303)


@router.post("/api/v1/sources/{source_id}/toggle")
async def toggle_source(
    source_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not check_auth(request):
        return RedirectResponse(url="/login")

    source = await db.get(JobSource, source_id)
    if source:
        source.is_active = not source.is_active
        await db.commit()

    return RedirectResponse(url="/sources", status_code=303)


@router.post("/api/v1/sources/{source_id}/delete")
async def delete_source(
    source_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not check_auth(request):
        return RedirectResponse(url="/login")

    source = await db.get(JobSource, source_id)
    if source:
        await db.delete(source)
        await db.commit()

    return RedirectResponse(url="/sources", status_code=303)