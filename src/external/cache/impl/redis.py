from __future__ import annotations

import functools
import json
import logging
from typing import Awaitable, Callable, Optional, ParamSpec, TypeVar, cast

import redis.asyncio as redis
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import ConnectionError, RedisError, TimeoutError

from ..base import BaseCache
from ..config import cache_settings


logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def redis_safe(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    @functools.wraps(fn)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if not args:
            raise RuntimeError("redis_safe expects bound method")
        self_obj = args[0]
        client = getattr(self_obj, "_client", None)
        if client is None:
            raise RuntimeError(
                f"{self_obj.__class__.__name__} not initialized"
            )

        try:
            return await fn(*args, **kwargs)
        except (ConnectionError, TimeoutError) as e:
            logger.exception(
                "Redis connection/timeout error in %s: %s", fn.__qualname__, e
            )
            raise
        except RedisError as e:
            logger.exception(
                "Redis command error in %s: %s", fn.__qualname__, e
            )
            raise

    return cast(Callable[P, Awaitable[R]], wrapper)


class RedisCache(BaseCache):
    """
    Redis-реализация для geo-districts.

    Ключ:
      <prefix>:cities_districts_json  -> одна JSON-строка:
          { "khabarovsk": [...], "vladivostok": [...] }
    """

    def __init__(self) -> None:
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None
        self._prefix = (
            cache_settings.cache_key_prefix.strip(":") or "geo_districts"
        )

    def _key_json(self) -> str:
        return f"{self._prefix}:cities_districts_json"

    async def init(self) -> None:
        if self._client is not None:
            logger.warning("RedisCache.init() called but already initialized")
            return

        url = cache_settings.cache_url.replace("cache://", "redis://", 1)
        self._pool = ConnectionPool.from_url(
            url,
            decode_responses=True,
            max_connections=cache_settings.cache_max_connections,
            socket_timeout=cache_settings.cache_socket_timeout,
            socket_connect_timeout=cache_settings.cache_socket_connect_timeout,
            health_check_interval=cache_settings.cache_health_check_interval,
        )
        self._client = redis.Redis(connection_pool=self._pool)
        await self._client.ping()
        logger.info("RedisCache connected")

    async def cleanup(self) -> None:
        if self._client is None:
            return
        try:
            await self._client.close()
            if self._pool is not None:
                await self._pool.disconnect(inuse_connections=True)
        finally:
            self._client = None
            self._pool = None
            logger.info("RedisCache closed")

    @redis_safe
    async def get_cities_districts_json(self) -> Optional[str]:
        key = self._key_json()
        value = await self._client.get(key)
        return value

    @redis_safe
    async def set_cities_districts_json(self, json_str: str) -> None:
        key = self._key_json()
        await self._client.set(key, json_str)

    @redis_safe
    async def delete_cities_districts_json(self) -> None:
        key = self._key_json()
        await self._client.delete(key)

    @redis_safe
    async def delete_city_from_json(self, city_code: str) -> bool:
        """
        Так как кеш один, делаем read-modify-write.

        Возвращаем True если city_code был и удалён.
        """
        key = self._key_json()
        raw = await self._client.get(key)
        if raw is None:
            return False

        try:
            payload = json.loads(raw)
        except Exception:
            await self._client.delete(key)
            return False

        if not isinstance(payload, dict) or city_code not in payload:
            return False

        payload.pop(city_code, None)
        await self._client.set(key, json.dumps(payload, ensure_ascii=False))
        return True
