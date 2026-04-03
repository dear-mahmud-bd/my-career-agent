import sys
from pathlib import Path
from loguru import logger
from app.core.config import settings

# ─────────────────────────────
# Log directory
# ─────────────────────────────
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# ─────────────────────────────
# Remove default logger
# ─────────────────────────────
logger.remove()

# ─────────────────────────────
# Console output
# ─────────────────────────────
logger.add(
    sys.stdout,
    level="DEBUG" if settings.debug else "INFO",
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    ),
    colorize=True,
)

# ─────────────────────────────
# General log file
# ─────────────────────────────
logger.add(
    LOG_DIR / "career_agent.log",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} | {message}",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
)

# ─────────────────────────────
# Error only log file
# ─────────────────────────────
logger.add(
    LOG_DIR / "errors.log",
    level="ERROR",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} | {message}",
    rotation="5 MB",
    retention="60 days",
    compression="zip",
)

# ─────────────────────────────
# LLM specific log file
# ─────────────────────────────
logger.add(
    LOG_DIR / "llm.log",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    filter=lambda record: "llm" in record["name"],
    rotation="5 MB",
    retention="14 days",
)
