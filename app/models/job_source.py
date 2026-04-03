from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class JobSource(Base, TimestampMixin):
    __tablename__ = "job_sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Source info
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)

    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # linkedin | linkedin_page | linkedin_post
    # indeed | glassdoor | zip_recruiter
    # facebook_group | facebook_page
    # career_page | rss | custom

    company_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Control
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    scrape_interval_hours: Mapped[int] = mapped_column(default=24)
    last_scraped_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    total_jobs_found: Mapped[int] = mapped_column(default=0)

    def __repr__(self) -> str:
        return f"<JobSource {self.name} ({self.source_type})>"