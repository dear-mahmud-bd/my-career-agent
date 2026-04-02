from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    # App
    app_name: str = Field(default="Career Agent")
    app_env: str = Field(default="development")
    debug: bool = Field(default=True)

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/career_agent.db"
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")

    # Telegram
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")

    # Groq
    groq_api_key: str = Field(default="")

    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="mistral")

    # Job Scraping
    job_scrape_interval_hours: int = Field(default=24)
    job_match_threshold: int = Field(default=65)

    # Skill Update
    skill_update_interval_days: int = Field(default=12)

    # CV
    cv_output_dir: Path = Field(default=Path("resume/output"))
    cv_template_dir: Path = Field(default=Path("resume/templates"))

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()