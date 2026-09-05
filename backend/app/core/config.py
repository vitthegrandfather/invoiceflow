"""Application settings. Fictional demo defaults only — never real credentials."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_name: str = "InvoiceFlow"
    environment: str = "demo"
    debug: bool = False
    api_prefix: str = ""

    database_url: str = "sqlite+aiosqlite:///./invoiceflow.db"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "demo-only-jwt-secret-not-for-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    demo_password: str = "demo-only"

    accounting_provider: str = "sandbox"
    extraction_provider: str = "sandbox"
    notification_provider: str = "sandbox"
    object_storage_provider: str = "sandbox"

    quickbooks_client_id: str | None = None
    quickbooks_client_secret: str | None = None
    xero_client_id: str | None = None
    xero_client_secret: str | None = None

    cors_origins: str = "*"
    log_level: str = "INFO"
    rate_limit_per_minute: int = 120

    n8n_webhook_base: str = "http://n8n:5678/webhook"
    ops_webhook_url: str = "http://localhost:8000/ops/alerts"

    seed_on_startup: bool = True

    database_echo: bool = False

    allowed_hosts: str = Field(default="*")


@lru_cache
def get_settings() -> Settings:
    return Settings()
