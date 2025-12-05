from __future__ import annotations

import logging
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


logger = logging.getLogger(__name__)


class OverpassSettings(BaseSettings):
    """
    Настройки клиента Overpass API.

    Используется для:
    - выполнения Overpass QL запросов к /api/interpreter
    - первичной/ленивой загрузки городов и районов из OSM
    """

    overpass_base_url: str = Field(
        default="https://overpass-api.de",
        description="Base URL Overpass API (without trailing slash)",
    )

    overpass_timeout_s: float = Field(
        default=120.0,
        description="HTTP client timeout in seconds for Overpass queries",
    )

    overpass_rps_limit: float = Field(
        default=1.0,
        description="Max Overpass requests per second (global limiter)",
    )

    overpass_retry_attempts: int = Field(
        default=3,
        description="How many retries on timeout/connection errors",
    )

    overpass_retry_backoff_s: float = Field(
        default=2.0,
        description="Base backoff seconds between retries",
    )

    model_config = SettingsConfigDict(
        env_file=Path(".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.debug(
            "Overpass settings loaded %s",
            "from .env" if Path(".env").exists() else "with defaults",
        )


overpass_settings = OverpassSettings()
