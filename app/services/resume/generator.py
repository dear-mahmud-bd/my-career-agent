import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.profile import Profile
from app.models.skill import Skill
from app.models.resume import Resume
from app.core.config import settings
from app.core.logger import logger


class CVGenerator:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.template_dir = settings.cv_template_dir
        self.output_dir = settings.cv_output_dir
        self.template_file = self.template_dir / "cv_template.tex"

    async def generate(self) -> Path | None:
        """Generate PDF CV from LaTeX template."""
        logger.info("Starting CV generation...")

        # Get profile
        profile = await self._get_profile()
        if not profile:
            logger.error(
                "No profile found. "
                "Please create your profile from the UI."
            )
            return None

        # Get skills
        skills = await self._get_skills()

        # Build version string
        version = datetime.now().strftime("v%Y.%m.%d")

        # Fill template
        latex_content = await self._fill_template(
            profile, skills, version
        )
        if not latex_content:
            return None

        # Save .tex file
        tex_filename = f"cv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tex"
        tex_path = self.output_dir / tex_filename
        tex_path.write_text(latex_content, encoding="utf-8")

        # Compile to PDF
        pdf_path = await self._compile_latex(tex_path)
        if not pdf_path:
            return None

        # Save to DB
        await self._save_to_db(
            version=version,
            pdf_path=pdf_path,
            tex_path=tex_path,
            skills=skills,
        )

        logger.success(f"CV generated: {pdf_path}")
        return pdf_path

    async def _fill_template(
        self,
        profile: Profile,
        skills: list[Skill],
        version: str,
    ) -> str | None:
        """Fill LaTeX template with profile data."""
        try:
            template = self.template_file.read_text(
                encoding="utf-8"
            )

            # Skills section
            skills_section = self._build_skills_section(skills)

            replacements = {
                "((FULL_NAME))": profile.full_name or "",
                "((CURRENT_TITLE))": profile.current_title or "",
                "((EMAIL))": profile.email or "",
                "((PHONE))": profile.phone or "",
                "((LOCATION))": profile.location or "",
                "((LINKEDIN_URL))": profile.linkedin_url or "#",
                "((GITHUB_URL))": profile.github_url or "#",
                "((PORTFOLIO_URL))": profile.portfolio_url or "",
                "((SUMMARY))": self._escape_latex(
                    profile.summary or ""
                ),
                "((SKILLS_SECTION))": skills_section,
                "((EXPERIENCE_SECTION))": "",
                "((EDUCATION_SECTION))": "",
                "((PROJECTS_SECTION))": "",
                "((LAST_UPDATED))": datetime.now().strftime(
                    "%B %Y"
                ),
                "((VERSION))": version,
            }

            for placeholder, value in replacements.items():
                template = template.replace(placeholder, value)

            return template

        except Exception as e:
            logger.error(f"Template filling failed: {e}")
            return None

    def _build_skills_section(
        self, skills: list[Skill]
    ) -> str:
        """Build LaTeX skills section grouped by category."""
        if not skills:
            return "No skills added yet."

        # Group by category
        categories: dict[str, list[Skill]] = {}
        for skill in skills:
            cat = skill.category or "Other"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(skill)

        lines = []
        for category, cat_skills in categories.items():
            skill_names = ", ".join(
                s.name for s in cat_skills
            )
            lines.append(
                f"\\textbf{{{category}:}} {skill_names}\\\\"
            )

        return "\n".join(lines)

    def _escape_latex(self, text: str) -> str:
        """Escape special LaTeX characters."""
        special_chars = {
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\textasciicircum{}",
        }
        for char, escaped in special_chars.items():
            text = text.replace(char, escaped)
        return text

    async def _compile_latex(
        self, tex_path: Path
    ) -> Path | None:
        """Compile .tex file to PDF using pdflatex."""
        try:
            result = subprocess.run(
                [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    "-output-directory",
                    str(self.output_dir),
                    str(tex_path),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            pdf_path = tex_path.with_suffix(".pdf")

            if result.returncode != 0:
                logger.error(
                    f"pdflatex failed:\n{result.stderr}"
                )
                return None

            if not pdf_path.exists():
                logger.error("PDF not generated")
                return None

            # Clean up auxiliary files
            for ext in [".aux", ".log", ".out"]:
                aux = tex_path.with_suffix(ext)
                if aux.exists():
                    aux.unlink()

            return pdf_path

        except subprocess.TimeoutExpired:
            logger.error("pdflatex timed out")
            return None
        except Exception as e:
            logger.error(f"LaTeX compilation error: {e}")
            return None

    async def _save_to_db(
        self,
        version: str,
        pdf_path: Path,
        tex_path: Path,
        skills: list[Skill],
    ) -> None:
        """Save CV record to database."""
        import json

        # Deactivate previous versions
        from sqlalchemy import update
        await self.db.execute(
            update(Resume).values(is_active=False)
        )

        skills_snapshot = json.dumps([
            {"name": s.name, "level": s.level}
            for s in skills
        ])

        resume = Resume(
            version=version,
            file_name=pdf_path.name,
            file_path=str(pdf_path),
            latex_path=str(tex_path),
            is_auto_generated=True,
            is_active=True,
            skills_snapshot=skills_snapshot,
        )
        self.db.add(resume)
        await self.db.commit()

    async def _get_profile(self) -> Profile | None:
        result = await self.db.execute(select(Profile))
        return result.scalar_one_or_none()

    async def _get_skills(self) -> list[Skill]:
        result = await self.db.execute(select(Skill))
        return result.scalars().all()