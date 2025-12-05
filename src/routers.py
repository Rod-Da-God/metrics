import logging
from typing import List

from fastapi import APIRouter, FastAPI
from districts.router import router as districts

logger = logging.getLogger(__name__)


def get_routers() -> List[APIRouter]:
    """
    Возвращает список маршрутов для подключения к приложению.
    """
    return [districts]


def setup_routers(app: FastAPI) -> None:
    """
    Подключает все маршруты к приложению и логирует их инициализацию.
    """
    for router in get_routers():
        app.include_router(router)
        logger.debug("Init router %s", getattr(router, "prefix", ""))
