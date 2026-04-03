import telegram
from telegram import Bot
from telegram.constants import ParseMode
from app.core.config import settings
from app.core.logger import logger


class TelegramNotifier:

    def __init__(self):
        self.token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self._bot: Bot | None = None

    def _get_bot(self) -> Bot:
        if not self._bot:
            self._bot = Bot(token=self.token)
        return self._bot

    async def is_available(self) -> bool:
        if not self.token or not self.chat_id:
            logger.warning(
                "Telegram token or chat ID not set in .env"
            )
            return False
        try:
            bot = self._get_bot()
            await bot.get_me()
            return True
        except Exception as e:
            logger.warning(f"Telegram not available: {e}")
            return False

    async def send_message(self, text: str) -> bool:
        """Send a plain message."""
        try:
            bot = self._get_bot()
            await bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
            )
            logger.debug("Telegram message sent")
            return True
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False

    async def send_job_match(self, match: dict) -> bool:
        """Send a job match notification."""
        try:
            score = match.get("match_score", 0)
            title = match.get("title", "Unknown")
            company = match.get("company", "Unknown")
            location = match.get("location", "N/A")
            url = match.get("url", "")
            work_type = match.get("work_type", "unknown")
            location_type = match.get("location_type", "unknown")
            match_reason = match.get("match_reason", "")
            matched_skills = match.get("matched_skills", "")
            missing_skills = match.get("missing_skills", "")
            salary_min = match.get("salary_min")
            salary_max = match.get("salary_max")
            llm_provider = match.get("llm_provider", "")

            # Score emoji
            if score >= 85:
                score_emoji = "🔥"
            elif score >= 70:
                score_emoji = "✅"
            elif score >= 55:
                score_emoji = "🟡"
            else:
                score_emoji = "🔵"

            # Work type emoji
            work_emoji = {
                "remote": "🌍",
                "onsite": "🏢",
                "hybrid": "🔄",
            }.get(work_type, "📍")

            # Location type
            loc_emoji = "🇧🇩" if location_type == "local" else "🌐"

            # Salary line
            salary_line = ""
            if salary_min and salary_max:
                salary_line = (
                    f"\n💰 *Salary:* "
                    f"${salary_min:,} — ${salary_max:,}"
                )
            elif salary_min:
                salary_line = f"\n💰 *Salary:* From ${salary_min:,}"

            # Skills lines
            skills_line = ""
            if matched_skills:
                skills_line += (
                    f"\n✔️ *Matched:* {matched_skills}"
                )
            if missing_skills:
                skills_line += (
                    f"\n❌ *Missing:* {missing_skills}"
                )

            message = (
                f"{score_emoji} *New Job Match — {score:.0f}% fit*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💼 *{title}*\n"
                f"🏬 *Company:* {company}\n"
                f"📍 *Location:* {location}\n"
                f"{work_emoji} *Work type:* {work_type.title()}\n"
                f"{loc_emoji} *Location type:* "
                f"{location_type.title()}"
                f"{salary_line}"
                f"\n\n💡 *Reason:* {match_reason}"
                f"{skills_line}\n\n"
                f"🔗 [Apply Here]({url})\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 _Matched by {llm_provider}_"
            )

            return await self.send_message(message)

        except Exception as e:
            logger.error(f"Failed to format job match message: {e}")
            return False

    async def send_skill_checkin_prompt(self) -> bool:
        """Send skill update check-in message."""
        message = (
            "📚 *Skill Check-In Time!*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "It's been a while — have you learned "
            "any new skills or tools recently?\n\n"
            "Reply with comma-separated skills:\n"
            "`Docker, GraphQL, System Design`\n\n"
            "Or reply `skip` to skip this check-in.\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🤖 _Career Agent — Skill Tracker_"
        )
        return await self.send_message(message)

    async def send_cv_generated(
        self,
        version: str,
        file_path: str,
    ) -> bool:
        """Send CV generated notification with PDF."""
        try:
            bot = self._get_bot()

            caption = (
                f"📄 *CV Updated — {version}*\n"
                f"Your resume has been regenerated "
                f"with your latest skills.\n"
                f"🤖 _Career Agent — CV Generator_"
            )

            with open(file_path, "rb") as pdf_file:
                await bot.send_document(
                    chat_id=self.chat_id,
                    document=pdf_file,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                )

            logger.info(f"CV sent via Telegram: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to send CV via Telegram: {e}")
            return False

    async def send_system_alert(
        self,
        title: str,
        message: str,
    ) -> bool:
        """Send a system alert message."""
        text = (
            f"⚠️ *System Alert*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"*{title}*\n\n"
            f"{message}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 _Career Agent_"
        )
        return await self.send_message(text)