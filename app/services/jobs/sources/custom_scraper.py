import httpx
from bs4 import BeautifulSoup
from app.core.logger import logger


async def scrape_custom_url(
    url: str,
    company_name: str = "",
    source_type: str = "custom",
) -> list[dict]:
    """
    Generic scraper for any custom URL added from the UI.
    Handles job boards, Facebook pages, LinkedIn pages etc.
    """
    jobs = []

    try:
        logger.info(f"Scraping custom URL [{source_type}]: {url}")

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers=headers,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        text_content = soup.get_text(separator="\n", strip=True)

        # Extract any visible job-like text blocks
        job_blocks = _extract_job_blocks(soup, url, company_name)

        if job_blocks:
            jobs.extend(job_blocks)
        else:
            # Fallback: store the whole page as one job entry
            # LLM matcher will extract what it needs
            title = soup.title.string if soup.title else url
            jobs.append({
                "title": str(title)[:200],
                "company": company_name or "Unknown",
                "location": "",
                "description": text_content[:3000],
                "url": url,
                "work_type": "unknown",
                "salary_min": None,
                "salary_max": None,
                "salary_currency": "USD",
                "source_type": source_type,
                "posted_at": "",
            })

        logger.info(
            f"Found {len(jobs)} jobs from custom URL: {url}"
        )

    except Exception as e:
        logger.error(f"Custom scraping failed for {url}: {e}")

    return jobs


def _extract_job_blocks(
    soup: BeautifulSoup,
    base_url: str,
    company_name: str,
) -> list[dict]:
    """Try to extract structured job blocks from the page."""
    jobs = []
    seen = set()

    # Common job listing container patterns
    selectors = [
        "article", "[class*='job']", "[class*='position']",
        "[class*='opening']", "[class*='vacancy']",
        "[class*='listing']", "[id*='job']",
    ]

    for selector in selectors:
        blocks = soup.select(selector)
        if not blocks:
            continue

        for block in blocks[:20]:
            text = block.get_text(strip=True)
            if len(text) < 20:
                continue

            # Find a link inside the block
            link = block.find("a", href=True)
            job_url = base_url
            if link:
                href = link.get("href", "")
                if href.startswith("http"):
                    job_url = href
                elif href.startswith("/"):
                    from urllib.parse import urlparse
                    parsed = urlparse(base_url)
                    job_url = f"{parsed.scheme}://{parsed.netloc}{href}"

            if job_url in seen:
                continue
            seen.add(job_url)

            # First line as title
            lines = [l for l in text.split("\n") if l.strip()]
            title = lines[0][:200] if lines else text[:100]

            jobs.append({
                "title": title,
                "company": company_name or "Unknown",
                "location": "",
                "description": text[:2000],
                "url": job_url,
                "work_type": "unknown",
                "salary_min": None,
                "salary_max": None,
                "salary_currency": "USD",
                "source_type": "custom",
                "posted_at": "",
            })

        if jobs:
            break

    return jobs