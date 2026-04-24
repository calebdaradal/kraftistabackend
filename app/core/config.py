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
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_bucket_web_settings: str = "web_settings"
    supabase_bucket_product_images: str = "product_images"
    supabase_signed_url_exp_seconds: int = 604800

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
