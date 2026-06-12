from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "FinTrader Hub"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    postgres_user: str = "fintrader"
    postgres_password: str = "fintrader_secret"
    postgres_db: str = "fintraderhub"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str = "postgresql://fintrader:fintrader_secret@localhost:5432/fintraderhub"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_url: str = "redis://localhost:6379/0"

    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    jwt_secret_key: str = Field(
        default="change-me-in-production-use-a-long-random-secret",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    finnhub_api_key: str = ""
    coingecko_api_key: str = ""
    alpha_vantage_api_key: str = ""
    exchange_rate_api_key: str = ""

    market_price_update_minutes: int = 5
    news_feed_update_minutes: int = 30
    news_expiration_days: int = 30
    market_price_cache_ttl_seconds: int = 60

    risk_free_rate: float = Field(default=0.0, ge=0.0, le=1.0)

    resend_api_key: str = ""
    resend_from_email: str = ""
    alert_email: str = ""

    api_key_encryption_key: str = ""

    log_format: str = "text"
    log_level: str = ""
    cors_origins: str = "*"
    auth_rate_limit_per_minute: int = Field(default=10, ge=1, le=1000)
    skip_startup_validation: bool = False
    skip_auto_migrations: bool = False

    @field_validator("database_url")
    @classmethod
    def validate_database_url_format(cls, value: str) -> str:
        if not value.startswith("postgresql://"):
            raise ValueError("DATABASE_URL must start with postgresql://")
        return value

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in {"text", "json"}:
            raise ValueError("LOG_FORMAT must be 'text' or 'json'")
        return normalized

    @property
    def resolved_log_level(self) -> str:
        if self.log_level:
            return self.log_level.upper()
        return "DEBUG" if self.app_env == "development" else "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
