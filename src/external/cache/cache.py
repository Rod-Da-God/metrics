from __future__ import annotations

import logging
from typing import Optional

from .base import BaseCache
from .impl.redis import RedisCache


logger = logging.getLogger(__name__)


class Cache:
    """
    Фасад над BaseCache для geo-districts.

    Хранит в Redis один JSON:
      city_code -> [districts...]

    - init/close на startup/shutdown
    - остальные слои используют только classmethod API
    """

    _impl: Optional[BaseCache] = None
    _is_initialized: bool = False

    @classmethod
    async def init(cls) -> None:
        if cls._is_initialized and cls._impl is not None:
            logger.warning("Cache.init() called but already initialized")
            return
        cls._impl = RedisCache()
        await cls._impl.init()
        cls._is_initialized = True
        logger.info("Cache initialized with %s", cls._impl.__class__.__name__)

    @classmethod
    async def close(cls) -> None:
        if not cls._is_initialized or cls._impl is None:
            logger.warning("Cache.close() called but not initialized")
            return
        try:
            await cls._impl.cleanup()
        finally:
            cls._impl = None
            cls._is_initialized = False
            logger.info("Cache closed")

    @classmethod
    def _require_impl(cls) -> BaseCache:
        if cls._impl is None or not cls._is_initialized:
            raise RuntimeError(
                "Cache is not initialized. Call Cache.init() first."
            )
        return cls._impl

    # ---------- districts cache ----------

    @classmethod
    async def get_cities_districts_json(cls) -> Optional[str]:
        """
        Вернуть кешированный JSON (строкой).
        Если кеша нет — None.
        """
        return await cls._require_impl().get_cities_districts_json()

    @classmethod
    async def set_cities_districts_json(cls, json_str: str) -> None:
        """
        Полностью перезаписать кеш JSON.
        """
        await cls._require_impl().set_cities_districts_json(json_str)

    @classmethod
    async def delete_cities_districts_json(cls) -> None:
        """
        Удалить кеш целиком (инвалидация).
        """
        await cls._require_impl().delete_cities_districts_json()

    # опционально (удобно сервису, но не обязательно)

    @classmethod
    async def delete_city_from_json(cls, city_code: str) -> bool:
        """
        Удалить город из JSON-кеша.

        Реализуется как:
          - get json
          - распарсить в dict
          - удалить ключ city_code
          - set json обратно

        Возвращает True если город был и удалён, иначе False.
        """
        return await cls._require_impl().delete_city_from_json(city_code)
