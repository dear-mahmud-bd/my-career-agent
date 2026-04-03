from sqlalchemy import String, Text, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class JobPreference(Base, TimestampMixin):
    __tablename__ = "job_preferences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Work type
    work_type: Mapped[str] = mapped_column(
        String(20), default="any"
    )
    # remote | onsite | hybrid | any

    # Location type
    location_type: Mapped[str] = mapped_column(
        String(20), default="both"
    )
    # local | foreign | both

    preferred_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    preferred_city: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Job titles to search for (comma separated)
    job_titles: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    # e.g: "Software Engineer, Backend Developer, Python Developer"

    # Experience level
    experience_level: Mapped[str] = mapped_column(
        String(20), default="mid"
    )
    # junior | mid | senior | any

    # Salary
    min_salary: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str] = mapped_column(String(10), default="USD")

    # Match threshold override (if null uses global setting)
    match_threshold: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Active
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<JobPreference {self.work_type} {self.location_type}>"