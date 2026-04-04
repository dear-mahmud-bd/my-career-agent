from pathlib import Path
from pypdf import PdfReader
from app.core.logger import logger


class CVParser:
    """Parse uploaded CV files to extract text content."""

    async def parse_pdf(self, file_path: Path) -> str:
        """Extract text from uploaded PDF CV."""
        try:
            reader = PdfReader(str(file_path))
            text_parts = []

            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            full_text = "\n".join(text_parts)
            logger.info(
                f"Parsed PDF: {len(full_text)} chars "
                f"from {len(reader.pages)} pages"
            )
            return full_text

        except Exception as e:
            logger.error(f"PDF parsing failed: {e}")
            return ""

    async def extract_skills_from_text(
        self,
        text: str,
    ) -> list[str]:
        """
        Use LLM to extract skills from CV text.
        Called after parsing uploaded CV.
        """
        from app.services.llm import llm_router

        prompt = f"""
Extract all technical skills, tools, frameworks, and
programming languages from this CV text.

CV TEXT:
{text[:3000]}

Respond with a JSON array of skill names only:
["Python", "Docker", "React", "PostgreSQL"]
"""
        response = await llm_router.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=500,
        )

        if not response.success:
            logger.error("LLM skill extraction failed")
            return []

        import json
        import re
        try:
            match = re.search(
                r'\[.*\]', response.content, re.DOTALL
            )
            if match:
                return json.loads(match.group())
        except Exception as e:
            logger.error(f"Skill parsing failed: {e}")

        return []