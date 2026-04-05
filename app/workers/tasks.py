import asyncio
from app.workers.celery_app import celery_app
from app.core.logger import logger


def run_async(coro):
    """Helper to run async functions inside Celery tasks."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ─────────────────────────────
# Task 1 — Scrape + Match Jobs
# ─────────────────────────────
@celery_app.task(
    name="app.workers.tasks.scrape_and_match_jobs",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def scrape_and_match_jobs(self):
    try:
        logger.info("Task: scrape_and_match_jobs started")
        result = run_async(_scrape_and_match())

        # Update scan status
        try:
            from app.api.v1.endpoints.jobs import _scan_status
            from datetime import datetime
            _scan_status["running"] = False
            _scan_status["last_result"] = result
        except Exception:
            pass

        logger.success(
            f"Task: scrape_and_match_jobs done → {result}"
        )
        return result
    except Exception as e:
        try:
            from app.api.v1.endpoints.jobs import _scan_status
            _scan_status["running"] = False
        except Exception:
            pass
        logger.error(f"Task: scrape_and_match_jobs failed → {e}")
        raise self.retry(exc=e)


async def _scrape_and_match() -> dict:
    from app.db.database import AsyncSessionLocal
    from app.services.jobs.job_service import JobService
    from app.services.matching.matcher import SkillMatcher
    from app.services.notifications.telegram import TelegramNotifier
    from app.core.config import settings

    notifier = TelegramNotifier()

    # ── Notify scan started ──
    await notifier.send_message(
        "🔍 *Job Scan Started*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"Scanning: {settings.job_sites}\n"
        f"Threshold: {settings.job_match_threshold}%\n"
        "I'll notify you when good matches are found.\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🤖 _Career Agent_"
    )

    async with AsyncSessionLocal() as db:
        job_service = JobService(db)
        new_jobs = await job_service.run_all_scrapers()

        matcher = SkillMatcher(db)
        matched = await matcher.match_all_pending_jobs()

    # ── Notify scan completed ──
    await notifier.send_message(
        "✅ *Job Scan Complete*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📥 New jobs found : {new_jobs}\n"
        f"🎯 Jobs matched   : {matched}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🤖 _Career Agent_"
    )

    return {
        "new_jobs_scraped": new_jobs,
        "jobs_matched": matched,
    }

# ─────────────────────────────
# Task 2 — Send Notifications
# ─────────────────────────────
@celery_app.task(
    name="app.workers.tasks.send_pending_notifications",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_pending_notifications(self):
    """Send Telegram notifications for top job matches."""
    try:
        logger.info("Task: send_pending_notifications started")
        result = run_async(_send_notifications())
        logger.success(
            f"Task: send_pending_notifications done → {result}"
        )
        return result
    except Exception as e:
        logger.error(
            f"Task: send_pending_notifications failed → {e}"
        )
        raise self.retry(exc=e)


async def _send_notifications() -> dict:
    from app.db.database import AsyncSessionLocal
    from app.services.matching.matcher import SkillMatcher
    from app.services.notifications.telegram import TelegramNotifier
    from app.models.job import JobMatch

    async with AsyncSessionLocal() as db:
        matcher = SkillMatcher(db)
        top_matches = await matcher.get_top_matches(limit=5)

        if not top_matches:
            logger.info("No new matches to notify.")
            return {"sent": 0}

        notifier = TelegramNotifier()
        sent_count = 0

        for match in top_matches:
            try:
                await notifier.send_job_match(match)

                # Mark as notified
                result = await db.get(JobMatch, match["match_id"])
                if result:
                    from datetime import datetime
                    result.notification_sent = True
                    result.notification_sent_at = (
                        datetime.now().isoformat()
                    )
                await db.commit()
                sent_count += 1

            except Exception as e:
                logger.error(
                    f"Failed to send notification "
                    f"for job {match['job_id']}: {e}"
                )
                continue

        return {"sent": sent_count}


# ─────────────────────────────
# Task 3 — Skill Check-in
# ─────────────────────────────
@celery_app.task(
    name="app.workers.tasks.send_skill_checkin",
    bind=True,
    max_retries=2,
    default_retry_delay=600,
)
def send_skill_checkin(self):
    """Send periodic skill update check-in via Telegram."""
    try:
        logger.info("Task: send_skill_checkin started")
        result = run_async(_send_skill_checkin())
        logger.success(
            f"Task: send_skill_checkin done → {result}"
        )
        return result
    except Exception as e:
        logger.error(f"Task: send_skill_checkin failed → {e}")
        raise self.retry(exc=e)


async def _send_skill_checkin() -> dict:
    from app.db.database import AsyncSessionLocal
    from app.services.notifications.telegram import TelegramNotifier
    from app.models.skill import SkillCheckin

    async with AsyncSessionLocal() as db:
        notifier = TelegramNotifier()
        await notifier.send_skill_checkin_prompt()

        # Log checkin in DB
        checkin = SkillCheckin(
            message="Skill check-in sent",
            response_received=False,
        )
        db.add(checkin)
        await db.commit()

        return {"checkin_sent": True}


# ─────────────────────────────
# Task 4 — Cleanup Expired Jobs
# ─────────────────────────────
@celery_app.task(
    name="app.workers.tasks.cleanup_expired_jobs",
    bind=True,
)
def cleanup_expired_jobs(self):
    """Mark old inactive jobs as expired."""
    try:
        logger.info("Task: cleanup_expired_jobs started")
        result = run_async(_cleanup_jobs())
        logger.success(
            f"Task: cleanup_expired_jobs done → {result}"
        )
        return result
    except Exception as e:
        logger.error(f"Task: cleanup_expired_jobs failed → {e}")


async def _cleanup_jobs() -> dict:
    from app.db.database import AsyncSessionLocal
    from app.models.job import Job
    from sqlalchemy import select, update
    from datetime import datetime, timedelta

    async with AsyncSessionLocal() as db:
        cutoff = datetime.now() - timedelta(days=30)

        # Mark jobs older than 30 days as expired
        result = await db.execute(
            update(Job)
            .where(
                Job.created_at < cutoff,
                Job.is_expired == False,
            )
            .values(is_expired=True, is_active=False)
        )
        await db.commit()

        return {"expired": result.rowcount}


# ─────────────────────────────
# Task 5 — Manual Trigger
# (called from UI dashboard)
# ─────────────────────────────
@celery_app.task(
    name="app.workers.tasks.manual_scrape",
)
def manual_scrape():
    """Manually trigger scrape + match from UI."""
    logger.info("Task: manual_scrape triggered from UI")
    return scrape_and_match_jobs.apply_async()


@celery_app.task(
    name="app.workers.tasks.regenerate_cv",
)
def regenerate_cv():
    """Manually trigger CV regeneration from UI."""
    try:
        logger.info("Task: regenerate_cv started")
        result = run_async(_regenerate_cv())
        logger.success(f"Task: regenerate_cv done → {result}")
        return result
    except Exception as e:
        logger.error(f"Task: regenerate_cv failed → {e}")


async def _regenerate_cv() -> dict:
    from app.db.database import AsyncSessionLocal
    from app.services.resume.generator import CVGenerator

    async with AsyncSessionLocal() as db:
        generator = CVGenerator(db)
        path = await generator.generate()
        return {"cv_path": str(path)}
    

