from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.notification import Notification
from app.services.notifications.telegram import TelegramNotifier
from app.core.logger import logger
from datetime import datetime


class NotificationService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.telegram = TelegramNotifier()

    async def send_and_log(
        self,
        notification_type: str,
        title: str,
        message: str,
        channel: str = "telegram",
        reference_id: int | None = None,
    ) -> Notification:
        """Send a notification and log it in DB."""

        notification = Notification(
            notification_type=notification_type,
            channel=channel,
            title=title,
            message=message,
            reference_id=reference_id,
            is_sent=False,
        )
        self.db.add(notification)
        await self.db.flush()

        # Send
        try:
            if channel == "telegram":
                success = await self.telegram.send_message(
                    message
                )
                notification.is_sent = success
                if not success:
                    notification.error_message = (
                        "Telegram send failed"
                    )
        except Exception as e:
            notification.error_message = str(e)
            logger.error(f"Notification send error: {e}")

        await self.db.commit()
        return notification

    async def get_recent(
        self,
        limit: int = 20,
    ) -> list[Notification]:
        result = await self.db.execute(
            select(Notification)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_unsent(self) -> list[Notification]:
        result = await self.db.execute(
            select(Notification).where(
                Notification.is_sent == False
            )
        )
        return result.scalars().all()

    async def mark_read(self, notification_id: int) -> None:
        notification = await self.db.get(
            Notification, notification_id
        )
        if notification:
            notification.is_read = True
            await self.db.commit()