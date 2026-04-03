from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class Skill(Base, TimestampMixin):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    # e.g: language | framework | tool | database | cloud | soft_skill

    level: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    # beginner | intermediate | advanced | expert

    years_used: Mapped[float] = mapped_column(default=0.0)
    is_primary: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Skill {self.name} ({self.level})>"


class SkillCheckin(Base, TimestampMixin):
    __tablename__ = "skill_checkins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    new_skills_added: Mapped[str | None] = mapped_column(Text, nullable=True)
    # stored as comma separated: "Docker, GraphQL, Redis"
    response_received: Mapped[bool] = mapped_column(default=False)

    def __repr__(self) -> str:
        return f"<SkillCheckin {self.created_at}>"