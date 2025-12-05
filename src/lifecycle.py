from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from typing import AsyncIterator

from fastapi import FastAPI

from external.cache.cache import Cache
from external.overpass.client import OverpassClient


logger = logging.getLogger(__name__)


async def startup() -> None:
    pass


async def shutdown() -> None:pass


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await startup()
    yield
    await shutdown()
