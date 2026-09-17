from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Kraftista Backend"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_exp_minutes: int = 10080  # 7 days
    admin_email: str | None = None
    admin_password: str | None = None
    admin_name: str = "Administrator"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080"
    b2_key_id: str | None = None
    b2_application_key: str | None = None
    b2_bucket_name: str = "Kraftista"
    b2_endpoint: str = "https://s3.us-east-005.backblazeb2.com"
    b2_signed_url_exp_seconds: int = 604800

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
