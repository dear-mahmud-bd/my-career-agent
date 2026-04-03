import feedparser
import httpx
from app.core.logger import logger


async def scrape_rss_feed(url: str, company_name: str = "") -> list[dict]:
    """Scrape jobs from an RSS feed URL."""
    jobs = []

    try:
        logger.info(f"Scraping RSS feed: {url}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            content = response.text

        feed = feedparser.parse(content)

        if not feed.entries:
            logger.warning(f"No entries found in RSS feed: {url}")
            return []

        for entry in feed.entries:
            job = _parse_rss_entry(entry, company_name, url)
            if job:
                jobs.append(job)

        logger.info(f"Found {len(jobs)} jobs from RSS: {url}")

    except Exception as e:
        logger.error(f"RSS scraping failed for {url}: {e}")

    return jobs


def _parse_rss_entry(entry, company_name: str, source_url: str) -> dict | None:
    """Parse a single RSS entry into our standard job dict."""
    try:
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()

        if not title or not link:
            return None

        description = entry.get("summary", "") or entry.get("content", "")
        if isinstance(description, list):
            description = description[0].get("value", "")

        return {
            "title": title,
            "company": company_name or entry.get("author", "Unknown"),
            "location": entry.get("location", ""),
            "description": str(description).strip(),
            "url": link,
            "work_type": "unknown",
            "salary_min": None,
            "salary_max": None,
            "salary_currency": "USD",
            "source_type": "rss",
            "posted_at": str(entry.get("published", "") or ""),
        }

    except Exception as e:
        logger.warning(f"Failed to parse RSS entry: {e}")
        return None