from celery import Celery
from celery.schedules import crontab
from app.core.config import settings
from app.core.logger import logger

# ─────────────────────────────
# Celery instance
# ─────────────────────────────
celery_app = Celery(
    "career_agent",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

# ─────────────────────────────
# Celery configuration
# ─────────────────────────────
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Dhaka",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
)

# ─────────────────────────────
# Periodic task schedule
# ─────────────────────────────
celery_app.conf.beat_schedule = {

    # Run job scraping every day at 9:00 AM
    "scrape-jobs-daily": {
        "task": "app.workers.tasks.scrape_and_match_jobs",
        "schedule": crontab(hour=9, minute=0),
    },

    # Run job scraping every day at 6:00 PM (second run)
    "scrape-jobs-evening": {
        "task": "app.workers.tasks.scrape_and_match_jobs",
        "schedule": crontab(hour=18, minute=0),
    },

    # Check skill update every 12 days at 10:00 AM
    "skill-checkin": {
        "task": "app.workers.tasks.send_skill_checkin",
        "schedule": crontab(
            hour=10,
            minute=0,
            day_of_month=f"*/{settings.skill_update_interval_days}",
        ),
    },

    # Send pending notifications every 30 minutes
    "send-notifications": {
        "task": "app.workers.tasks.send_pending_notifications",
        "schedule": crontab(minute="*/30"),
    },

    # Clean up expired jobs every Sunday at midnight
    "cleanup-expired-jobs": {
        "task": "app.workers.tasks.cleanup_expired_jobs",
        "schedule": crontab(hour=0, minute=0, day_of_week=0),
    },
}

logger.info("Celery app configured ✅")