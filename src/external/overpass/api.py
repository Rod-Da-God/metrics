from __future__ import annotations

import functools
import logging
from typing import Any, Awaitable, Callable, Optional, ParamSpec, TypeVar, cast

import httpx
from httpx import AsyncClient, ConnectError, HTTPError, TimeoutException

from .config import overpass_settings


logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def api_endpoint(
    path: str, method: str = "POST"
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """
    Декоратор для методов OverpassApiClient.

    - не создаёт клиент
    - проверяет init()
    - делает HTTP запрос
    - передает json-ответ в метод через data=
    - логирует и пробрасывает ошибки
    """

    def decorator(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if not args:
                raise RuntimeError("api_endpoint expects bound method")

            self_obj = args[0]
            client: Optional[AsyncClient] = getattr(self_obj, "_client", None)
            base_url: Optional[str] = getattr(self_obj, "_base_url", None)
            if client is None or base_url is None:
                raise RuntimeError(
                    f"{self_obj.__class__.__name__} not initialized: call init() first"
                )

            url = base_url.rstrip("/") + path

            try:
                logger.debug("HTTP %s %s", method.upper(), url)

                # Извлекаем query из kwargs и формируем form data
                query_str = kwargs.pop("query", None)
                if query_str:
                    # Overpass API ожидает query в form data
                    form_data = {"data": query_str}
                    resp = await client.post(url, data=form_data)
                else:
                    resp = await client.request(method.upper(), url, **kwargs)
                
                resp.raise_for_status()
                data = resp.json()

                logger.debug(
                    "HTTP %s %s -> %s", method.upper(), url, resp.status_code
                )
                # ВАЖНО: передаём query обратно в метод вместе с data
                return await fn(*args, query=query_str, data=data)

            except (TimeoutException, ConnectError) as e:
                logger.exception("Overpass connection/timeout error: %s", e)
                raise

            except HTTPError as e:
                status = getattr(e.response, "status_code", None)
                body = getattr(e.response, "text", "")
                logger.exception(
                    "Overpass HTTP error: %s %s -> status=%s body=%s err=%s",
                    method,
                    url,
                    status,
                    body[:500],
                    e,
                )
                raise

        return cast(Callable[P, Awaitable[R]], wrapper)

    return decorator


class OverpassApiClient:
    """
    Реальный HTTP-клиент Overpass API.

    Отвечает за:
    - управление AsyncClient (init/close)
    - выполнение запросов к /api/interpreter
    - базовую обработку ошибок
    - (в будущем) retry/backoff/rate-limit
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout_s: Optional[float] = None,
    ) -> None:
        self._base_url = base_url or overpass_settings.overpass_base_url
        self._timeout_s = timeout_s or overpass_settings.overpass_timeout_s

        self._client: Optional[AsyncClient] = None

    async def init(self) -> None:
        if self._client is not None:
            logger.warning(
                "OverpassApiClient.init() called but already initialized"
            )
            return

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(self._timeout_s),
        )
        logger.info(
            "OverpassApiClient initialized: base_url=%s timeout=%s",
            self._base_url,
            self._timeout_s,
        )

    async def close(self) -> None:
        if self._client is None:
            logger.warning(
                "OverpassApiClient.close() called but not initialized"
            )
            return
        await self._client.aclose()
        self._client = None
        logger.info("OverpassApiClient closed")

    @api_endpoint("/api/interpreter", method="POST")
    async def execute(self, *, query: str, data: Any) -> dict:
        """
        Выполнить Overpass QL запрос.

        query — строка overpass QL.
        Возвращает сырой JSON dict.
        """
        # Декоратор уже сделал request и передал data=resp.json()
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict from Overpass, got {type(data)}")
        return data