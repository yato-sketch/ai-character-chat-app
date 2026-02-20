"""
Application configuration from environment and constants.
"""
import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class TavusConfig:
    """Tavus API configuration."""

    api_key: str
    replica_id: str
    base_url: str = "https://tavusapi.com"
    request_timeout_seconds: int = 30
    poll_interval_seconds: int = 10
    poll_max_wait_seconds: int = 20 * 60  # 20 minutes

    @property
    def videos_url(self) -> str:
        return f"{self.base_url}/v2/videos"


@dataclass(frozen=True)
class AppConfig:
    """Application configuration."""

    groq_api_key: str
    tavus: TavusConfig
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "AppConfig":
        groq_key = os.getenv("GROQ_API_KEY", "").strip()
        tavus_key = os.getenv("TAVUS_API_KEY", "").strip()
        replica_id = os.getenv("TAVUS_REPLICA_ID", "").strip()

        if not groq_key or not tavus_key:
            raise ValueError(
                "Missing required env: GROQ_API_KEY and TAVUS_API_KEY must be set in .env"
            )

        tavus = TavusConfig(
            api_key=tavus_key,
            replica_id=replica_id or "rcefb7292e",  # fallback for demo
        )
        return cls(groq_api_key=groq_key, tavus=tavus)


def get_config() -> AppConfig:
    """Load and return application config. Cached in practice via module import."""
    return AppConfig.from_env()
