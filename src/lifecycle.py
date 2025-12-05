from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from typing import AsyncIterator

from fastapi import FastAPI
from database.core.connection import init_db




logger = logging.getLogger(__name__)


async def startup() -> None:
    await init_db(use_create_all=False)



async def shutdown() -> None:pass


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await startup()
    yield
    await shutdown()
