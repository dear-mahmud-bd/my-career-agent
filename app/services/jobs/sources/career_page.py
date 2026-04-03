import httpx
from bs4 import BeautifulSoup
from app.core.logger import logger


async def scrape_career_page(
    url: str,
    company_name: str = "",
) -> list[dict]:
    """
    Scrape a company career page for job listings.
    This is a generic scraper — works for most career pages.
    """
    jobs = []

    try:
        logger.info(f"Scraping career page: {url}")

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers=headers,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Generic job link detection
        job_links = _find_job_links(soup, url)

        for link_data in job_links[:30]:  # max 30 per page
            jobs.append({
                "title": link_data["title"],
                "company": company_name or _extract_company(url),
                "location": "",
                "description": "",
                "url": link_data["url"],
                "work_type": "unknown",
                "salary_min": None,
                "salary_max": None,
                "salary_currency": "USD",
                "source_type": "career_page",
                "posted_at": "",
            })

        logger.info(
            f"Found {len(jobs)} jobs from career page: {url}"
        )

    except Exception as e:
        logger.error(f"Career page scraping failed for {url}: {e}")

    return jobs


def _find_job_links(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """Find job listing links on a career page."""
    job_links = []
    seen_urls = set()

    # Keywords that suggest a job listing link
    job_keywords = [
        "job", "career", "position", "role", "opening",
        "vacancy", "engineer", "developer", "manager",
        "designer", "analyst", "intern"
    ]

    for a_tag in soup.find_all("a", href=True):
        href = a_tag.get("href", "").strip()
        text = a_tag.get_text(strip=True)

        if not href or not text or len(text) < 5:
            continue

        # Build full URL
        if href.startswith("http"):
            full_url = href
        elif href.startswith("/"):
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            full_url = f"{parsed.scheme}://{parsed.netloc}{href}"
        else:
            continue

        if full_url in seen_urls:
            continue

        # Check if link looks like a job
        combined = (href + " " + text).lower()
        if any(kw in combined for kw in job_keywords):
            seen_urls.add(full_url)
            job_links.append({
                "title": text[:200],
                "url": full_url,
            })

    return job_links


def _extract_company(url: str) -> str:
    """Extract company name from URL."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    return domain.split(".")[0].title()