import logging
from time import time
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware


logger = logging.getLogger(__name__)


def add_cors_middleware(app: FastAPI) -> None:
    origins = [
        "http://localhost:5173/",
        "http://localhost:5173",
        "http://127.0.0.1:5173/",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


async def log_requests(request: Request, call_next: Callable) -> None:
    start_time = time()
    response = await call_next(request)
    process_time = time() - start_time
    logger.info(
        f"\"{request.method} {request.url.path} HTTP/{request.scope['http_version']}\" "
        f"from {request.client.host} status - {response.status_code} time - {process_time:.3f}s"
    )
    return response


def setup_middlewares(app: FastAPI) -> None:
    add_cors_middleware(app)
    app.middleware("http")(log_requests)
