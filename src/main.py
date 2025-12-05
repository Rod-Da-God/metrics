import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
import uvicorn

from config import settings
from exc_handler import setup_exception_handlers
from middleware import setup_middlewares
from routers import setup_routers
from utils.log_conf import setup_logging
from database.core.connection import init_db


setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Управление жизненным циклом приложения.
    """
    logger.info("Starting application...")
    
    await init_db(use_create_all=True)
    logger.info("Database connection established successfully")
    yield
    


app = FastAPI(
    title="Analytics API",
    description="API для приема и обработки аналитических событий",
    lifespan=lifespan
)

setup_middlewares(app=app)
setup_exception_handlers(app=app)
setup_routers(app=app)


if __name__ == "__main__":
    logger.info("Starting server on %s:%s", settings.host, settings.port)
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.uc_log_level,
        reload=False,
    )