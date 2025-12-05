from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class BaseCache(ABC):
    """
    Абстрактное хранилище для geo-districts сервиса.

    Хранит:
    - один JSON в формате:
        city_code -> [districts...]
    """

    @abstractmethod
    async def init(self) -> None:
        """Поднять соединение/пул, ping и т.п."""
        raise NotImplementedError

    @abstractmethod
    async def cleanup(self) -> None:
        """Корректно закрыть соединение/пул."""
        raise NotImplementedError

    @abstractmethod
    async def get_cities_districts_json(self) -> Optional[str]:
        """
        Вернуть JSON-строку из кеша.
        Если ключа нет — None.
        """
        raise NotImplementedError

    @abstractmethod
    async def set_cities_districts_json(self, json_str: str) -> None:
        """
        Полностью записать JSON-строку в кеш.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_cities_districts_json(self) -> None:
        """
        Удалить ключ JSON-кеша (инвалидация).
        Idempotent: ок если ключа нет.
        """
        raise NotImplementedError

    # опционально

    @abstractmethod
    async def delete_city_from_json(self, city_code: str) -> bool:
        """
        Удалить один city_code из кеша,
        перезаписав кеш целиком.

        True если ключ существовал, False если нет или кеш пуст.
        """
        raise NotImplementedError
