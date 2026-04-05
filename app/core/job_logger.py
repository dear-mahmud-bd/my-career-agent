import json
from pathlib import Path
from datetime import datetime
from app.core.logger import logger


JOB_LOG_DIR = Path("logs/job_results")
JOB_LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_job_result(
    job: dict,
    match_score: float,
    matched_skills: str,
    missing_skills: str,
    match_reason: str,
    llm_provider: str,
    notification_sent: bool,
) -> None:
    """
    Write one job result to today's log file.
    Format is human-readable + JSON for future parsing.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = JOB_LOG_DIR / f"{today}.log"

    # Determine action
    if match_score >= 85:
        action = "HIGHLY_RECOMMENDED — Apply immediately"
    elif match_score >= 70:
        action = "RECOMMENDED — Worth applying"
    elif match_score >= 55:
        action = "CONSIDER — Review manually"
    else:
        action = "SKIP — Low match"

    # Notification status
    notif_status = "✅ Sent to Telegram" if notification_sent \
        else "⏳ Below threshold"

    entry = {
        "timestamp": datetime.now().isoformat(),
        "title": job.get("title", ""),
        "company": job.get("company", ""),
        "location": job.get("location", ""),
        "work_type": job.get("work_type", ""),
        "location_type": job.get("location_type", ""),
        "url": job.get("url", ""),
        "match_score": match_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "match_reason": match_reason,
        "action": action,
        "notification": notif_status,
        "llm_provider": llm_provider,
    }

    # Human-readable line
    line = (
        f"\n{'='*60}\n"
        f"[{entry['timestamp']}]\n"
        f"JOB    : {entry['title']} @ {entry['company']}\n"
        f"LOC    : {entry['location']} "
        f"| {entry['work_type']} | {entry['location_type']}\n"
        f"URL    : {entry['url']}\n"
        f"SCORE  : {match_score:.1f}%\n"
        f"ACTION : {action}\n"
        f"MATCH  : {matched_skills}\n"
        f"MISS   : {missing_skills}\n"
        f"REASON : {match_reason}\n"
        f"NOTIFY : {notif_status}\n"
        f"LLM    : {llm_provider}\n"
        f"JSON   : {json.dumps(entry)}\n"
    )

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line)

    logger.debug(
        f"Job logged: {entry['title']} | {match_score:.1f}%"
    )