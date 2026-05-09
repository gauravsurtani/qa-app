from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_base_url: str = "http://localhost:8000"
    sqlite_path: str = "./data/qa.db"
    log_level: str = "INFO"
    session_secret: str = Field(default="", min_length=32)
    room_ttl_hours: int = 24

    email_provider: str = "resend"
    email_api_key: str = ""
    email_from_address: str = "qa@askup.app"
    email_from_name: str = "AskUp"

    rate_limit_questions_per_min: int = 5
    rate_limit_upvotes_per_min: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
