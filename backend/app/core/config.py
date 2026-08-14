from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Calibre Aviation Academy CRM"
    app_env: str = "development"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Default to SQLite for local/dev without Docker. Override with PostgreSQL in .env for production.
    database_url: str = "sqlite+aiosqlite:///./calibre_crm.db"
    database_url_sync: str = "sqlite:///./calibre_crm.db"

    jwt_secret_key: str = "change-me-to-a-long-random-secret-key-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin"
    s3_bucket_name: str = "calibre-crm"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False

    redis_url: str = "redis://localhost:6379/0"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@calibreaviation.academy"

    sms_provider: str = ""
    sms_api_key: str = ""
    sms_sender_id: str = ""

    whatsapp_provider: str = ""
    whatsapp_api_key: str = ""
    whatsapp_phone_number_id: str = ""

    push_provider: str = ""
    push_api_key: str = ""

    zoom_account_id: str = ""
    zoom_client_id: str = ""
    zoom_client_secret: str = ""

    google_client_id: str = ""

    # Vision AI for punch selfie grooming (hair, facial grooming, appearance)
    gemini_api_key: str = ""
    openai_api_key: str = ""
    grooming_vision_model: str = ""  # default: gemini-2.0-flash or gpt-4o-mini

    rate_limit_per_minute: int = 60
    hot_lead_contact_hours: int = 2
    attendance_warning_threshold: float = 75.0

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in {"development", "dev", "local", "test"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
