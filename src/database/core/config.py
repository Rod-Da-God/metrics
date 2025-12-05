from pathlib import Path  # Импорт Path
import ssl
from typing import Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """
    Настройки базы данных, загружаемые из .env файла.

    Пример .env файла:
    DB_USER=postgres
    DB_PASSWORD=secret_password
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=mydatabase
    DB_ECHO=False

    DB_POOL_SIZE=20
    DB_MAX_OVERFLOW=50
    DB_CONNECT_TIMEOUT=10
    """

    DB_DIALECT: str = Field("postgresql")
    DB_DRIVER: str = Field("asyncpg")
    DB_USER: Optional[str] = Field(default=None)
    DB_PASSWORD: Optional[SecretStr] = Field(default=None)
    DB_HOST: str = Field("localhost")
    DB_PORT: int = Field(5432)
    DB_NAME: Optional[str] = Field(default=None)

    DB_ECHO: bool = Field(False)
    DB_POOL_SIZE: int = Field(5)
    DB_MAX_OVERFLOW: int = Field(10)
    DB_CONNECT_TIMEOUT: int = Field(30)

    DB_SSL_ENABLED: bool = Field(True)
    DB_SSL_MODE: str = Field("require")
    DB_SSL_CA_PATH: Optional[str] = Field(default=None)
    DB_SSL_CERT_PATH: Optional[str] = Field(default=None)
    DB_SSL_KEY_PATH: Optional[str] = Field(default=None)

    model_config = SettingsConfigDict(
        env_file=Path(".env"),  # Автоматически ищет .env в корне приложения
        env_file_encoding="utf-8",
        extra="ignore",  # Игнорирует переменные, которые не указаны в классе
    )

    @field_validator("DB_SSL_MODE")
    @classmethod
    def validate_ssl_mode(cls, v: str) -> str:
        valid_modes = [
            "disable",
            "allow",
            "prefer",
            "require",
            "verify-ca",
            "verify-full",
        ]
        if v not in valid_modes:
            raise ValueError(
                f"DB_SSL_MODE должен быть одним из: {', '.join(valid_modes)}"
            )
        return v

    @property
    def sqlalchemy_url(self) -> str:
        """
        Формирует URL для подключения к базе данных.

        Пример результата:
        'postgresql+asyncpg://postgres:secret_password@localhost:5432/mydatabase'
        """
        return (
            f"{self.DB_DIALECT}+{self.DB_DRIVER}://{self.DB_USER}:{self.DB_PASSWORD.get_secret_value()}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    def get_ssl_context(self) -> dict:
        if not self.DB_SSL_ENABLED:
            return {}

        ssl_context = ssl.create_default_context(cafile=self.DB_SSL_CA_PATH)

        if self.DB_SSL_MODE == "verify-full":
            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED
        elif self.DB_SSL_MODE == "verify-ca":
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_REQUIRED
        elif self.DB_SSL_MODE == "require":
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        if self.DB_SSL_CERT_PATH and self.DB_SSL_KEY_PATH:
            ssl_context.load_cert_chain(
                certfile=self.DB_SSL_CERT_PATH, keyfile=self.DB_SSL_KEY_PATH
            )

        return {"ssl": ssl_context}


settings = DatabaseSettings()
