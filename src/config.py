import logging
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


logger = logging.getLogger(__name__)


class FastAPISettings(BaseSettings):
    host: str = Field("127.0.0.1")
    port: int = Field("8000")
    uc_log_level: str = Field("critical")

    model_config = SettingsConfigDict(
        env_file=Path("../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )
    logger.debug(
        "Load settings for FastAPI %s",
        "from .env" if Path("../../.env").exists() else "with defaults",
    )


settings = FastAPISettings()
