from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/german_helper.db"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash-lite"
    admin_token: str = "change-me"
    max_daily_articles: int = 10
    max_daily_generations: int = 30
    frontend_origin: str = "http://localhost:5173"
    news_provider: str = "gnews"
    gnews_api_key: str | None = None
    news_language: str = "de"
    news_country: str = "de"
    news_max_articles: int = 10
    news_refresh_min_seconds: int = 300
    news_rss_fallback: bool = False
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()

def ensure_data_dir() -> None:
    s = get_settings()
    if s.database_url.startswith("sqlite:///"):
        Path(s.database_url.removeprefix("sqlite:///" )).parent.mkdir(parents=True, exist_ok=True)
