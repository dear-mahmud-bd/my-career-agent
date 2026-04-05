from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):

    # ─────────────────────────────
    # App
    # ─────────────────────────────
    app_name: str = Field(default="")
    app_env: str = Field(default="")
    debug: bool = Field(default=True)
    secret_key: str = Field(default="")
    ui_username: str = Field(default="")
    ui_password: str = Field(default="chageme")

    # ─────────────────────────────
    # Database
    # ─────────────────────────────
    database_url: str = Field(default="")

    # ─────────────────────────────
    # Redis
    # ─────────────────────────────
    redis_url: str = Field(default="")

    # ─────────────────────────────
    # Telegram
    # ─────────────────────────────
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")

    # ─────────────────────────────
    # LLM
    # ─────────────────────────────
    llm_provider: str = Field(default="")
    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="")
    ollama_base_url: str = Field(default="")
    ollama_model: str = Field(default="")

    # ─────────────────────────────
    # Job Scraping
    # ─────────────────────────────
    job_scrape_interval_hours: int = Field(default=0)
    job_match_threshold: int = Field(default=0)
    job_sites: str = Field(default="")

    @property
    def job_sites_list(self) -> list[str]:
        return [s.strip() for s in self.job_sites.split(",") if s.strip()]

    # ─────────────────────────────
    # Skill Update
    # ─────────────────────────────
    skill_update_interval_days: int = Field(default=0)

    # ─────────────────────────────
    # CV
    # ─────────────────────────────
    cv_output_dir: Path = Field(default=Path("resume/output"))
    cv_template_dir: Path = Field(default=Path("resume/templates"))

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }


settings = Settings()