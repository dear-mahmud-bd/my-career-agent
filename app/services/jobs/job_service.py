from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.job import Job
from app.models.job_source import JobSource
from app.models.job_preference import JobPreference
from app.services.jobs.sources.jobspy_scraper import scrape_jobspy
from app.services.jobs.sources.rss_scraper import scrape_rss_feed
from app.services.jobs.sources.career_page import scrape_career_page
from app.services.jobs.sources.custom_scraper import scrape_custom_url
from app.core.logger import logger
from datetime import datetime
from app.core.config import settings


class JobService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_all_scrapers(self) -> int:
        """
        Run all active scrapers.
        Even with no sources in DB, scrapes from
        JOB_SITES in .env automatically.
        Returns total new jobs saved.
        """
        logger.info("Starting job scraping run...")

        preferences = await self._get_preferences()
        if not preferences:
            logger.warning(
                "No job preferences set. "
                "Please set preferences from the UI."
            )
            return 0

        job_titles = []
        if preferences.job_titles:
            job_titles = [
                t.strip()
                for t in preferences.job_titles.split(",")
                if t.strip()
            ]

        if not job_titles:
            logger.warning("No job titles in preferences.")
            return 0

        all_raw_jobs = []

        # ── 1. Always scrape from .env JOB_SITES ──
        logger.info(
            f"Scraping default boards: {settings.job_sites_list}"
        )
        try:
            jobspy_jobs = await scrape_jobspy(
                job_titles=job_titles,
                location=preferences.preferred_city or "",
                work_type=preferences.work_type,
            )
            all_raw_jobs.extend(jobspy_jobs)
            logger.info(
                f"Default boards: {len(jobspy_jobs)} jobs found"
            )
        except Exception as e:
            logger.error(f"Default board scraping failed: {e}")

        # ── 2. Also scrape custom sources from DB ──
        sources = await self._get_active_sources()
        if sources:
            logger.info(
                f"Scraping {len(sources)} custom sources from DB"
            )
        for source in sources:
            try:
                if source.source_type == "rss":
                    jobs = await scrape_rss_feed(
                        source.url,
                        source.company_name or "",
                    )
                elif source.source_type == "career_page":
                    jobs = await scrape_career_page(
                        source.url,
                        source.company_name or "",
                    )
                else:
                    jobs = await scrape_custom_url(
                        source.url,
                        source.company_name or "",
                        source.source_type,
                    )

                all_raw_jobs.extend(jobs)
                source.last_scraped_at = datetime.now().isoformat()
                source.total_jobs_found += len(jobs)

            except Exception as e:
                logger.error(f"Source {source.url} failed: {e}")
                continue

        await self.db.commit()

        # ── 3. Save new jobs ──
        new_count = await self._save_new_jobs(
            all_raw_jobs, preferences
        )
        logger.success(
            f"Scraping done. "
            f"Scraped: {len(all_raw_jobs)}, "
            f"New: {new_count}"
        )
        return new_count

    async def _save_new_jobs(
        self,
        raw_jobs: list[dict],
        preferences: JobPreference,
    ) -> int:
        """Save only new jobs (skip duplicates by URL)."""
        new_count = 0

        for raw in raw_jobs:
            url = raw.get("url", "").strip()
            if not url:
                continue

            # Skip if already exists
            existing = await self.db.execute(
                select(Job).where(Job.url == url)
            )
            if existing.scalar_one_or_none():
                continue

            # Detect location type
            location_type = self._detect_location_type(
                raw, preferences
            )

            job = Job(
                title=raw.get("title", ""),
                company=raw.get("company", ""),
                location=raw.get("location", ""),
                description=raw.get("description", ""),
                url=url,
                work_type=raw.get("work_type", "unknown"),
                location_type=location_type,
                salary_min=raw.get("salary_min"),
                salary_max=raw.get("salary_max"),
                salary_currency=raw.get("salary_currency", "USD"),
                source_type=raw.get("source_type", "unknown"),
                posted_at=raw.get("posted_at", ""),
            )
            self.db.add(job)
            new_count += 1

        await self.db.commit()
        return new_count

    def _detect_location_type(
        self,
        raw: dict,
        preferences: JobPreference,
    ) -> str:
        """Detect if job is local or foreign."""
        location = (raw.get("location", "") or "").lower()
        preferred_country = (
            preferences.preferred_country or ""
        ).lower()
        preferred_city = (
            preferences.preferred_city or ""
        ).lower()

        if not location:
            return "unknown"

        if preferred_city and preferred_city in location:
            return "local"
        if preferred_country and preferred_country in location:
            return "local"
        if "remote" in location:
            return "foreign"

        return "foreign"

    async def _get_preferences(self) -> JobPreference | None:
        result = await self.db.execute(
            select(JobPreference).where(
                JobPreference.is_active == True
            )
        )
        return result.scalar_one_or_none()

    async def _get_active_sources(self) -> list[JobSource]:
        result = await self.db.execute(
            select(JobSource).where(JobSource.is_active == True)
        )
        return result.scalars().all()

    async def get_unmatched_jobs(self) -> list[Job]:
        """Get jobs that haven't been matched yet."""
        from app.models.job import JobMatch
        matched_ids = select(JobMatch.job_id)
        result = await self.db.execute(
            select(Job).where(
                Job.id.not_in(matched_ids),
                Job.is_active == True,
            )
        )
        return result.scalars().all()

    async def get_matched_jobs(
        self,
        min_score: float = 65.0,
        limit: int = 20,
    ) -> list[dict]:
        """Get jobs with match scores above threshold."""
        from app.models.job import JobMatch
        from sqlalchemy import desc

        result = await self.db.execute(
            select(Job, JobMatch)
            .join(JobMatch, Job.id == JobMatch.job_id)
            .where(JobMatch.match_score >= min_score)
            .order_by(desc(JobMatch.match_score))
            .limit(limit)
        )
        rows = result.all()

        jobs = []
        for job, match in rows:
            jobs.append({
                "id": job.id,
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
                "notification_sent": match.notification_sent,
                "user_applied": match.user_applied,
            })

        return jobs