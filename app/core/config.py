from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    app_name: str = "Arbi3"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_log_level: str = "INFO"

    database_url: str = Field(
        default="mysql+asyncmy://arbi3:arbi3_password@mysql:3306/arbi3?charset=utf8mb4"
    )
    alembic_database_url: str = Field(
        default="mysql+pymysql://arbi3:arbi3_password@mysql:3306/arbi3?charset=utf8mb4"
    )

    default_collection_mode: str = "all"
    default_quote_interval_ms: int = 1000
    min_quote_interval_ms: int = 250
    max_quote_interval_ms: int = 60000

    spread_bucket_flush_seconds: int = 10
    spread_window_refresh_seconds: int = 60
    spread_bucket_retention_hours: int = 48


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
