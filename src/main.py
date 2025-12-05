import logging

from contextlib import asynccontextmanager
from typing import AsyncIterator


from fastapi import FastAPI
import uvicorn

from config import settings
from exc_handler import setup_exception_handlers
from lifecycle import lifespan
from middleware import setup_middlewares
from routers import setup_routers
from utils.log_conf import setup_logging

from database.core.connection import init_db
from external.cache.cache import Cache
from external.overpass.client import OverpassClient

setup_logging()

logger = logging.getLogger(__name__)





@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await startup()
    yield
    await shutdown()

app = FastAPI(lifespan=lifespan)

setup_middlewares(app=app)
setup_exception_handlers(app=app)
setup_routers(app=app)

