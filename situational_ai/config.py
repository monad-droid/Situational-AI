"""Configuration — loaded from .env and config.json. Runs 100% locally."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_DIR = Path(__file__).resolve().parent.parent / "data"
CONFIG_FILE = CONFIG_DIR / "config.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API keys — user provides their own
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    # Model selection
    anthropic_model: str = "claude-sonnet-4-20250514"
    openai_model: str = "gpt-4o"

    # Coach behaviour
    check_interval_minutes: int = 60
    coach_intensity: int = Field(default=7, ge=1, le=10)

    def get_provider(self) -> Literal["anthropic", "openai"]:
        if self.anthropic_api_key:
            return "anthropic"
        if self.openai_api_key:
            return "openai"
        raise ValueError(
            "No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in your .env file. "
            "This runs on YOUR credits — no server costs."
        )


def load_settings() -> Settings:
    return Settings()


# --- Per-user threshold config stored in data/config.json ---

DEFAULT_CONFIG = {
    "thresholds": [
        {
            "id": "weight_upper",
            "metric": "body_mass",
            "direction": "above",
            "value": 170.0,
            "unit": "lb",
            "goal_value": 165.0,
            "coach_persona": "You are a relentless but caring health coach. You do NOT let the user off the hook. You check in frequently, give actionable advice, and celebrate small wins. Be direct, motivating, and persistent — like a real coach who actually cares.",
        }
    ],
    "user_profile": {
        "name": "",
        "timezone": "America/New_York",
    },
}


def load_user_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    # First run — write defaults
    CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
    return DEFAULT_CONFIG


def save_user_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))
