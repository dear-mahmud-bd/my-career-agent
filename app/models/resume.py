from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class Resume(Base, TimestampMixin):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # File info
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    # e.g: "v1.0", "v1.1", "2025-01"

    file_name: Mapped[str] = mapped_column(String(200), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    latex_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Type
    is_auto_generated: Mapped[bool] = mapped_column(Boolean, default=True)
    is_uploaded: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON snapshot of skills at time of generation

    def __repr__(self) -> str:
        return f"<Resume {self.version} {self.file_name}>"