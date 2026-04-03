from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Type
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # job_match | skill_checkin | cv_generated | system

    # Channel
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    # telegram | whatsapp | messenger

    # Content
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Reference
    reference_id: Mapped[int | None] = mapped_column(nullable=True)
    # job_id or resume_id depending on type

    # Status
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Notification {self.notification_type} via {self.channel}>"