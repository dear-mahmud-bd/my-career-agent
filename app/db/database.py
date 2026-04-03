from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.logger import logger

# ─────────────────────────────
# Engine
# ─────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False}
)

# ─────────────────────────────
# Session factory
# ─────────────────────────────
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# ─────────────────────────────
# Dependency for FastAPI routes
# ─────────────────────────────
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()