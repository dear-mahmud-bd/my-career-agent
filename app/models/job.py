from sqlalchemy import String, Text, Boolean, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Job info
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    company: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)

    # Work type
    work_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # remote | onsite | hybrid

    location_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # local | foreign

    # Salary
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Source tracking
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_expired: Mapped[bool] = mapped_column(Boolean, default=False)
    posted_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expires_at: Mapped[str | None] = mapped_column(String(50), nullable=True)

    def __repr__(self) -> str:
        return f"<Job {self.title} at {self.company}>"


class JobMatch(Base, TimestampMixin):
    __tablename__ = "job_matches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    job_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Match result
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    match_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    matched_skills: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_skills: Mapped[str | None] = mapped_column(Text, nullable=True)

    # LLM used for this match
    llm_provider_used: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Notification
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    notification_sent_at: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # User feedback
    user_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    user_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"<JobMatch job_id={self.job_id} score={self.match_score}>"