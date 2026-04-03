from jobspy import scrape_jobs
from app.core.logger import logger
from app.core.config import settings
import pandas as pd


async def scrape_jobspy(
    job_titles: list[str],
    location: str = "",
    work_type: str = "any",
    results_per_site: int = 20,
) -> list[dict]:
    """
    Scrape jobs from LinkedIn, Indeed, Glassdoor, ZipRecruiter.
    job_titles  : list of titles to search
    location    : city/country string
    work_type   : remote | onsite | hybrid | any
    """

    all_jobs = []

    # Map work_type to jobspy format
    is_remote = None
    if work_type == "remote":
        is_remote = True
    elif work_type == "onsite":
        is_remote = False

    sites = settings.job_sites.split(",")
    sites = [s.strip() for s in sites]

    for title in job_titles:
        logger.info(f"Scraping '{title}' from {sites}")
        try:
            jobs_df: pd.DataFrame = scrape_jobs(
                site_name=sites,
                search_term=title,
                location=location if location else None,
                is_remote=is_remote,
                results_wanted=results_per_site,
                hours_old=48,
                country_indeed="worldwide",
            )

            if jobs_df is None or jobs_df.empty:
                logger.warning(f"No jobs found for '{title}'")
                continue

            for _, row in jobs_df.iterrows():
                job = _normalize_job(row, title)
                if job:
                    all_jobs.append(job)

            logger.info(
                f"Found {len(jobs_df)} jobs for '{title}'"
            )

        except Exception as e:
            logger.error(f"JobSpy scraping failed for '{title}': {e}")
            continue

    logger.info(f"Total jobs scraped via JobSpy: {len(all_jobs)}")
    return all_jobs


def _normalize_job(row, search_title: str) -> dict | None:
    """Normalize a jobspy row into our standard job dict."""
    try:
        url = str(row.get("job_url", "")).strip()
        title = str(row.get("title", "")).strip()
        company = str(row.get("company", "")).strip()

        if not url or not title or not company:
            return None

        # Detect work type
        work_type = "unknown"
        is_remote = row.get("is_remote", None)
        if is_remote is True:
            work_type = "remote"
        elif is_remote is False:
            work_type = "onsite"

        # Salary
        salary_min = None
        salary_max = None
        salary_currency = "USD"
        try:
            salary_min = int(row.get("min_amount", 0) or 0)
            salary_max = int(row.get("max_amount", 0) or 0)
            salary_currency = str(
                row.get("currency", "USD") or "USD"
            )
        except Exception:
            pass

        return {
            "title": title,
            "company": company,
            "location": str(row.get("location", "") or ""),
            "description": str(row.get("description", "") or ""),
            "url": url,
            "work_type": work_type,
            "salary_min": salary_min if salary_min else None,
            "salary_max": salary_max if salary_max else None,
            "salary_currency": salary_currency,
            "source_type": str(row.get("site", "unknown")),
            "posted_at": str(row.get("date_posted", "") or ""),
        }

    except Exception as e:
        logger.warning(f"Failed to normalize job row: {e}")
        return None