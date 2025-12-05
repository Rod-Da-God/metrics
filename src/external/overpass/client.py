import logging
from typing import Optional

from .api import OverpassApiClient


logger = logging.getLogger(__name__)


class OverpassClient:
    """
    Фасад уровня приложения.

    - создаёт один OverpassApiClient на весь проект
    - init/close вызываются в startup/shutdown
    - остальные слои используют только classmethod API
    """

    _impl: Optional[OverpassApiClient] = None
    _is_initialized: bool = False

    @classmethod
    async def init(cls) -> None:
        if cls._is_initialized and cls._impl is not None:
            logger.warning(
                "OverpassClient.init() called but already initialized"
            )
            return
        cls._impl = OverpassApiClient()
        await cls._impl.init()
        cls._is_initialized = True
        logger.info("OverpassClient initialized")

    @classmethod
    async def close(cls) -> None:
        if not cls._is_initialized or cls._impl is None:
            logger.warning("OverpassClient.close() called but not initialized")
            return
        try:
            await cls._impl.close()
        finally:
            cls._impl = None
            cls._is_initialized = False
            logger.info("OverpassClient closed")

    @classmethod
    def _require_impl(cls) -> OverpassApiClient:
        if cls._impl is None or not cls._is_initialized:
            raise RuntimeError(
                "OverpassClient not initialized. Call init() first."
            )
        return cls._impl

    # --- Публичные методы фасада ---
    @classmethod
    async def execute(cls, query: str) -> dict:
        impl = cls._require_impl()
        return await impl.execute(query=query)
