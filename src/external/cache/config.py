import logging
from pathlib import Path
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


logger = logging.getLogger(__name__)


class CacheSettings(BaseSettings):
    """
    Настройки cache для SEO-render сервиса.

    cache используется как основное хранилище:
    - seo:html:banner:<slug>
    - seo:html:index
    - seo:sitemap
    - seo:slugs
    """

    cache_user: Optional[str] = Field(
        default=None, description="Cache username (optional)"
    )
    cache_password: Optional[SecretStr] = Field(
        default=None, description="Cache password (optional)"
    )
    cache_host: str = Field(default="localhost", description="Cache host")
    cache_port: int = Field(default=6379, description="Cache port")
    cache_db: int = Field(default=0, description="Cache database number")

    cache_decode_responses: bool = Field(
        default=True, description="Decode responses to str"
    )
    cache_max_connections: int = Field(
        default=20, description="Connection pool max size"
    )
    cache_socket_timeout: int = Field(
        default=5, description="Read/Write socket timeout (sec)"
    )
    cache_socket_connect_timeout: int = Field(
        default=10, description="Connect timeout (sec)"
    )
    cache_health_check_interval: int = Field(
        default=15, description="Health check interval (sec)"
    )

    cache_key_prefix: str = Field(
        default="geo", description="Prefix for all keys"
    )

    model_config = SettingsConfigDict(
        env_file=Path(".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def cache_url(self) -> str:
        """
        Собирает cache:// URL с учётом user/password (если заданы).
        Формат:
          cache://user:password@host:port/db
          cache://host:port/db
        """
        user_part = f"{self.cache_user}:" if self.cache_user else ""
        password_part = (
            f"{self.cache_password.get_secret_value()}@"
            if self.cache_password
            else ""
        )
        return (
            f"cache://{user_part}{password_part}"
            f"{self.cache_host}:{self.cache_port}/{self.cache_db}"
        )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.debug(
            "cache settings loaded %s",
            "from .env" if Path(".env").exists() else "with defaults",
        )


cache_settings = CacheSettings()
