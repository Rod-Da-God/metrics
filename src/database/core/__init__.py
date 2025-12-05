# src/my_db_library/core/__init__.py
from .config import settings
from .connection import connection, init_db

__all__ = ["settings", "connection", "init_db"]
