import shutil
from pathlib import Path
from fastapi import APIRouter, Request, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.resume import Resume
from app.core.security import check_auth
from app.core.config import settings
from app.services.resume.generator import CVGenerator
from app.services.resume.parser import CVParser
from app.services.llm import llm_router

router = APIRouter()
templates = Jinja2Templates(directory="app/ui/templates")


@router.get("/resume", response_class=HTMLResponse)
async def resume_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not check_auth(request):
        return RedirectResponse(url="/login")

    result = await db.execute(
        select(Resume).order_by(Resume.created_at.desc())
    )
    resumes = result.scalars().all()
    llm_provider = await llm_router.get_active_provider()

    return templates.TemplateResponse(
        "resume.html",
        {
            "request": request,
            "active_page": "resume",
            "llm_provider": llm_provider,
            "resumes": resumes,
        },
    )


@router.post("/api/v1/resume/generate")
async def generate_resume(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not check_auth(request):
        return RedirectResponse(url="/login")

    generator = CVGenerator(db)
    pdf_path = await generator.generate()

    if pdf_path:
        return RedirectResponse(
            url="/resume?message=CV+generated+successfully&message_type=success",
            status_code=303,
        )
    return RedirectResponse(
        url="/resume?message=CV+generation+failed.+Check+your+profile.&message_type=error",
        status_code=303,
    )


@router.post("/api/v1/resume/upload")
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not check_auth(request):
        return RedirectResponse(url="/login")

    # Save uploaded file
    upload_path = settings.cv_output_dir / file.filename
    with open(upload_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Parse and extract skills
    parser = CVParser()
    text = await parser.parse_pdf(upload_path)
    extracted_skills = await parser.extract_skills_from_text(text)

    # Save skills to DB
    if extracted_skills:
        from app.models.skill import Skill
        for skill_name in extracted_skills:
            skill = Skill(
                name=skill_name.strip(),
                level="intermediate",
                category="tool",
            )
            db.add(skill)
        await db.commit()

    # Save resume record
    from datetime import datetime
    resume = Resume(
        version=datetime.now().strftime("uploaded-%Y%m%d"),
        file_name=file.filename,
        file_path=str(upload_path),
        is_uploaded=True,
        is_auto_generated=False,
        is_active=True,
        notes=f"Extracted {len(extracted_skills)} skills",
    )
    db.add(resume)
    await db.commit()

    return RedirectResponse(
        url=f"/resume?message=CV+uploaded.+{len(extracted_skills)}+skills+extracted&message_type=success",
        status_code=303,
    )


@router.get("/api/v1/resume/{resume_id}/download")
async def download_resume(
    resume_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not check_auth(request):
        return RedirectResponse(url="/login")

    resume = await db.get(Resume, resume_id)
    if not resume or not Path(resume.file_path).exists():
        return RedirectResponse(
            url="/resume?message=File+not+found&message_type=error",
            status_code=303,
        )

    return FileResponse(
        path=resume.file_path,
        filename=resume.file_name,
        media_type="application/pdf",
    )