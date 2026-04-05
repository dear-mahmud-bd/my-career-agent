import json
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.skill import Skill
from app.models.job import Job, JobMatch
from app.models.job_preference import JobPreference
from app.services.llm import llm_router
from app.core.config import settings
from app.core.logger import logger


MATCH_SYSTEM_PROMPT = """
You are an expert career advisor and technical recruiter.
Your job is to analyze how well a candidate's skills match a job description.
You must always respond with valid JSON only. No explanation outside JSON.
"""

MATCH_PROMPT_TEMPLATE = """
Analyze this job match and respond with JSON only.

CANDIDATE SKILLS:
{skills}

JOB TITLE: {job_title}
COMPANY: {company}
JOB DESCRIPTION:
{job_description}

Respond with this exact JSON format:
{{
    "match_score": <integer 0-100>,
    "match_reason": "<one sentence summary of why this score>",
    "matched_skills": "<comma separated skills candidate has that match>",
    "missing_skills": "<comma separated important skills candidate is missing>",
    "recommendation": "<apply | consider | skip>"
}}

Scoring guide:
- 85-100 : Strong match, most requirements met
- 70-84  : Good match, minor gaps
- 55-69  : Partial match, some gaps
- 40-54  : Weak match, significant gaps
- 0-39   : Poor match, not recommended
"""


class SkillMatcher:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def match_all_pending_jobs(self) -> int:
        """
        Match all unmatched jobs against candidate skills.
        Returns count of jobs matched.
        """
        logger.info("Starting skill matching run...")

        # Get candidate skills
        skills = await self._get_skills()
        if not skills:
            logger.warning(
                "No skills found in profile. "
                "Please add your skills from the UI."
            )
            return 0

        skills_text = self._format_skills(skills)

        # Get unmatched jobs
        unmatched_jobs = await self._get_unmatched_jobs()
        if not unmatched_jobs:
            logger.info("No new jobs to match.")
            return 0

        logger.info(
            f"Matching {len(unmatched_jobs)} jobs "
            f"against {len(skills)} skills..."
        )

        matched_count = 0
        for job in unmatched_jobs:
            try:
                result = await self._match_single_job(
                    job, skills_text
                )
                if result:
                    matched_count += 1
            except Exception as e:
                logger.error(
                    f"Matching failed for job {job.id}: {e}"
                )
                continue

        await self.db.commit()
        logger.success(
            f"Matching complete. {matched_count} jobs matched."
        )
        return matched_count

    async def _match_single_job(
        self,
        job: Job,
        skills_text: str,
    ) -> JobMatch | None:
        description = job.description or job.title
        if not description or len(description) < 20:
            return None

        description = description[:3000]

        prompt = MATCH_PROMPT_TEMPLATE.format(
            skills=skills_text,
            job_title=job.title,
            company=job.company,
            job_description=description,
        )

        response = await llm_router.generate(
            prompt=prompt,
            system_prompt=MATCH_SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=500,
        )

        if not response.success:
            logger.error(
                f"LLM failed for job {job.id}: {response.error}"
            )
            return None

        parsed = self._parse_llm_response(response.content)
        if not parsed:
            return None

        match_score = float(parsed.get("match_score", 0))
        matched_skills = parsed.get("matched_skills", "")
        missing_skills = parsed.get("missing_skills", "")
        match_reason = parsed.get("match_reason", "")

        # Check if above threshold for notification
        threshold = settings.job_match_threshold
        notification_sent = False

        match = JobMatch(
            job_id=job.id,
            match_score=match_score,
            match_reason=match_reason,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            llm_provider_used=response.provider,
        )
        self.db.add(match)

        # ── Send Telegram if good match ──
        if match_score >= threshold:
            try:
                from app.services.notifications.telegram import (
                    TelegramNotifier,
                )
                notifier = TelegramNotifier()
                job_dict = {
                    "job_id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "location": job.location or "",
                    "url": job.url,
                    "work_type": job.work_type or "unknown",
                    "location_type": job.location_type or "unknown",
                    "salary_min": job.salary_min,
                    "salary_max": job.salary_max,
                    "match_score": match_score,
                    "match_reason": match_reason,
                    "matched_skills": matched_skills,
                    "missing_skills": missing_skills,
                    "llm_provider": response.provider,
                }
                sent = await notifier.send_job_match(job_dict)
                if sent:
                    notification_sent = True
                    from datetime import datetime
                    match.notification_sent = True
                    match.notification_sent_at = (
                        datetime.now().isoformat()
                    )
            except Exception as e:
                logger.error(f"Telegram notify failed: {e}")

        # ── Write to job result log ──
        from app.core.job_logger import log_job_result
        log_job_result(
            job={
                "title": job.title,
                "company": job.company,
                "location": job.location or "",
                "work_type": job.work_type or "",
                "location_type": job.location_type or "",
                "url": job.url,
            },
            match_score=match_score,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            match_reason=match_reason,
            llm_provider=response.provider,
            notification_sent=notification_sent,
        )

        logger.info(
            f"'{job.title}' @ '{job.company}' "
            f"→ {match_score:.1f}% [{response.provider}]"
            f"{' 🔔' if notification_sent else ''}"
        )

        return match

    def _parse_llm_response(self, content: str) -> dict | None:
        """Parse JSON from LLM response safely."""
        try:
            # Try direct parse first
            return json.loads(content.strip())
        except json.JSONDecodeError:
            pass

        # Try extracting JSON block
        try:
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                return json.loads(match.group())
        except json.JSONDecodeError:
            pass

        logger.warning(f"Could not parse JSON from: {content[:200]}")
        return None

    def _format_skills(self, skills: list[Skill]) -> str:
        """Format skills list into readable text for LLM."""
        lines = []
        for skill in skills:
            line = f"- {skill.name}"
            if skill.level:
                line += f" ({skill.level})"
            if skill.years_used and skill.years_used > 0:
                line += f" — {skill.years_used} years"
            if skill.category:
                line += f" [{skill.category}]"
            lines.append(line)
        return "\n".join(lines)

    async def _get_skills(self) -> list[Skill]:
        result = await self.db.execute(select(Skill))
        return result.scalars().all()

    async def _get_unmatched_jobs(self) -> list[Job]:
        matched_ids = select(JobMatch.job_id)
        result = await self.db.execute(
            select(Job).where(
                Job.id.not_in(matched_ids),
                Job.is_active == True,
            )
        )
        return result.scalars().all()

    async def get_top_matches(
        self,
        limit: int = 10,
        min_score: float | None = None,
    ) -> list[dict]:
        """Get top job matches above threshold."""
        from sqlalchemy import desc

        threshold = min_score or settings.job_match_threshold

        result = await self.db.execute(
            select(Job, JobMatch)
            .join(JobMatch, Job.id == JobMatch.job_id)
            .where(
                JobMatch.match_score >= threshold,
                JobMatch.notification_sent == False,
                JobMatch.user_dismissed == False,
            )
            .order_by(desc(JobMatch.match_score))
            .limit(limit)
        )

        matches = []
        for job, match in result.all():
            matches.append({
                "job_id": job.id,
                "match_id": match.id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "url": job.url,
                "work_type": job.work_type,
                "location_type": job.location_type,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "match_score": match.match_score,
                "match_reason": match.match_reason,
                "matched_skills": match.matched_skills,
                "missing_skills": match.missing_skills,
                "llm_provider": match.llm_provider_used,
            })

        return matches