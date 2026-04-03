from app.db.database import engine
from app.models import Base
from app.core.logger import logger


async def init_db() -> None:
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.success("Database tables created ✅")