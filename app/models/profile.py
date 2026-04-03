from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class Profile(Base, TimestampMixin):
    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Personal info
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Professional summary
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    years_of_experience: Mapped[int] = mapped_column(default=0)

    # Availability
    is_actively_looking: Mapped[bool] = mapped_column(Boolean, default=True)
    available_from: Mapped[str | None] = mapped_column(String(50), nullable=True)

    def __repr__(self) -> str:
        return f"<Profile {self.full_name}>"