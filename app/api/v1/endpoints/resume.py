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

    # ── Validation ──────────────────────────
    # 1. File must exist
    if not file or not file.filename:
        return RedirectResponse(
            url="/resume?message=No+file+selected&message_type=error",
            status_code=303,
        )

    # 2. Must be PDF
    if not file.filename.lower().endswith(".pdf"):
        return RedirectResponse(
            url="/resume?message=Only+PDF+files+are+allowed&message_type=error",
            status_code=303,
        )

    # 3. Check content type
    if file.content_type not in ["application/pdf", "application/octet-stream"]:
        return RedirectResponse(
            url="/resume?message=Invalid+file+type.+PDF+only&message_type=error",
            status_code=303,
        )

    # 4. Read file and check size (max 10MB)
    contents = await file.read()
    max_size = 10 * 1024 * 1024  # 10MB
    if len(contents) == 0:
        return RedirectResponse(
            url="/resume?message=Uploaded+file+is+empty&message_type=error",
            status_code=303,
        )
    if len(contents) > max_size:
        return RedirectResponse(
            url="/resume?message=File+too+large.+Max+10MB+allowed&message_type=error",
            status_code=303,
        )

    # 5. Check PDF magic bytes (real PDF starts with %PDF)
    if not contents[:4] == b"%PDF":
        return RedirectResponse(
            url="/resume?message=Invalid+PDF+file+content&message_type=error",
            status_code=303,
        )

    # ── Save file ───────────────────────────
    import uuid
    safe_filename = f"{uuid.uuid4().hex}_{file.filename}"
    upload_path = settings.cv_output_dir / safe_filename

    with open(upload_path, "wb") as f:
        f.write(contents)

    # ── Parse and extract skills ─────────────
    parser = CVParser()
    text = await parser.parse_pdf(upload_path)

    if not text or len(text.strip()) < 50:
        return RedirectResponse(
            url="/resume?message=Could+not+extract+text+from+PDF.+Is+it+scanned%3F&message_type=error",
            status_code=303,
        )

    extracted_skills = await parser.extract_skills_from_text(text)

    # ── Save skills to DB ────────────────────
    saved_skills = 0
    if extracted_skills:
        from app.models.skill import Skill
        from sqlalchemy import select as sa_select
        for skill_name in extracted_skills:
            skill_name = skill_name.strip()
            if not skill_name:
                continue
            # Skip duplicates
            existing = await db.scalar(
                sa_select(Skill).where(
                    Skill.name.ilike(skill_name)
                )
            )
            if not existing:
                skill = Skill(
                    name=skill_name,
                    level="intermediate",
                    category="tool",
                )
                db.add(skill)
                saved_skills += 1
        await db.commit()

    # ── Save resume record ───────────────────
    from datetime import datetime
    resume = Resume(
        version=datetime.now().strftime("uploaded-%Y%m%d-%H%M"),
        file_name=file.filename,
        file_path=str(upload_path),
        is_uploaded=True,
        is_auto_generated=False,
        is_active=True,
        notes=f"Extracted {saved_skills} new skills",
    )
    db.add(resume)
    await db.commit()

    logger.info(
        f"CV uploaded: {file.filename} "
        f"| {saved_skills} new skills saved"
    )

    return RedirectResponse(
        url=f"/resume?message=CV+uploaded.+{saved_skills}+new+skills+extracted&message_type=success",
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