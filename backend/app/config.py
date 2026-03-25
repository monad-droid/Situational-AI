"""Backend configuration — loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/situational_ai"
    secret_key: str = "change-me-in-production"

    # AI Providers
    openai_api_key: str = ""
    nudge_model: str = "gpt-5-mini"
    anthropic_api_key: str = ""
    chat_model: str = "claude-haiku-4-5-20251001"

    # Apple Sign In
    apple_team_id: str = ""
    apple_bundle_id: str = "com.cmdloop.situationalai"
    apple_key_id: str = ""
    apple_private_key_path: str = "./keys/AuthKey.p8"

    # APNs
    apns_key_path: str = "./keys/AuthKey.p8"
    apns_key_id: str = ""
    apns_team_id: str = ""
    apns_topic: str = "com.cmdloop.situationalai"
    apns_use_sandbox: bool = True

    # Coaching limits
    daily_chat_message_limit: int = 10
    min_nudge_interval_minutes: int = 180  # 3 hours between nudges per threshold


settings = Settings()
