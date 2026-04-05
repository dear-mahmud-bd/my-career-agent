import asyncio
from datetime import datetime
from app.core.logger import logger
from app.core.config import settings


class ScanManager:
    """
    Manages continuous job scanning loop.
    Runs forever until explicitly stopped.
    """

    def __init__(self):
        self.is_running: bool = False
        self.is_scanning: bool = False
        self.scan_count: int = 0
        self.started_at: str | None = None
        self.last_scan_at: str | None = None
        self.last_result: dict | None = None
        self.next_scan_at: str | None = None
        self._task: asyncio.Task | None = None

    def get_status(self) -> dict:
        return {
            "is_running": self.is_running,
            "is_scanning": self.is_scanning,
            "scan_count": self.scan_count,
            "started_at": self.started_at,
            "last_scan_at": self.last_scan_at,
            "last_result": self.last_result,
            "next_scan_at": self.next_scan_at,
            "interval_hours": settings.job_scrape_interval_hours,
        }

    def start(self):
        """Start the continuous scan loop."""
        if self.is_running:
            logger.warning("Scan manager already running")
            return

        self.is_running = True
        self.started_at = datetime.now().isoformat()
        self._task = asyncio.create_task(self._loop())
        logger.success("Scan manager started ✅")

    def stop(self):
        """Stop the scan loop."""
        self.is_running = False
        if self._task:
            self._task.cancel()
        logger.info("Scan manager stopped")

    async def run_once(self):
        """Run a single scan immediately."""
        if self.is_scanning:
            logger.warning("Scan already in progress")
            return

        await self._do_scan()

    async def _loop(self):
        """
        Main scan loop.
        Runs scan → waits interval → repeats forever.
        """
        logger.info(
            f"Scan loop started. "
            f"Interval: every {settings.job_scrape_interval_hours}h"
        )

        while self.is_running:
            await self._do_scan()

            if not self.is_running:
                break

            # Wait for next interval
            interval_seconds = (
                settings.job_scrape_interval_hours * 3600
            )
            next_scan = datetime.fromtimestamp(
                datetime.now().timestamp() + interval_seconds
            )
            self.next_scan_at = next_scan.isoformat()

            logger.info(
                f"Next scan at: {next_scan.strftime('%Y-%m-%d %H:%M')}"
            )

            # Sleep in small chunks so we can stop cleanly
            elapsed = 0
            while elapsed < interval_seconds and self.is_running:
                await asyncio.sleep(60)
                elapsed += 60

    async def _do_scan(self):
        """Run one full scrape + match + notify cycle."""
        from app.db.database import AsyncSessionLocal
        from app.services.jobs.job_service import JobService
        from app.services.matching.matcher import SkillMatcher
        from app.services.notifications.telegram import (
            TelegramNotifier,
        )

        self.is_scanning = True
        self.scan_count += 1
        scan_started = datetime.now()

        logger.info(
            f"Starting scan #{self.scan_count}..."
        )

        notifier = TelegramNotifier()

        try:
            # ── Notify start ──
            await notifier.send_message(
                f"🔍 *Job Scan \#{self.scan_count} Started*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 Sources : linkedin, indeed, glassdoor\n"
                f"🎯 Threshold : {settings.job_match_threshold}%\n"
                f"🕐 Time : "
                f"{scan_started.strftime('%Y-%m-%d %H:%M')}\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "🤖 _Career Agent_"
            )

            async with AsyncSessionLocal() as db:
                job_service = JobService(db)
                new_jobs = await job_service.run_all_scrapers()

                matcher = SkillMatcher(db)
                matched = await matcher.match_all_pending_jobs()

            duration = (
                datetime.now() - scan_started
            ).seconds

            result = {
                "scan_number": self.scan_count,
                "new_jobs_scraped": new_jobs,
                "jobs_matched": matched,
                "duration_seconds": duration,
                "scanned_at": scan_started.isoformat(),
            }

            self.last_result = result
            self.last_scan_at = datetime.now().isoformat()

            # ── Notify complete ──
            await notifier.send_message(
                f"✅ *Scan #{self.scan_count} Complete*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"📥 New jobs : {new_jobs}\n"
                f"🎯 Matched  : {matched}\n"
                f"⏱ Duration : {duration}s\n"
                f"🔄 Next scan in "
                f"{settings.job_scrape_interval_hours}h\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "🤖 _Career Agent_"
            )

            logger.success(
                f"Scan #{self.scan_count} done — "
                f"new: {new_jobs}, matched: {matched}, "
                f"duration: {duration}s"
            )

        except asyncio.CancelledError:
            logger.info("Scan cancelled")
            raise

        except Exception as e:
            logger.error(f"Scan #{self.scan_count} failed: {e}")
            self.last_result = {"error": str(e)}

            try:
                await notifier.send_message(
                    f"❌ *Scan #{self.scan_count} Failed*\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"Error: {str(e)[:200]}\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "🤖 _Career Agent_"
                )
            except Exception:
                pass

        finally:
            self.is_scanning = False


# ─────────────────────────────
# Single global instance
# ─────────────────────────────
scan_manager = ScanManager()