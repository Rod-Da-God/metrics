import logging
import os
from pathlib import Path
import sys
import time
import traceback
from typing import List

from dotenv import load_dotenv
from loguru import logger


libs_to_mute = [
    "botocore",
    "boto3",
    "aiobotocore",
    "urllib3",
    "python_multipart.multipart",
    "httpcore._trace",
]


def mute_loggers(
    names: List[str],
    level: int = logging.CRITICAL,
    clear_handlers: bool = True,
    stop_propagation: bool = True,
):
    """
    Красиво и централизованно заглушает логи указанных библиотек.

    Args:
        names: список имён логгеров (например: ["boto3", "httpx._trace"])
        level: уровень логирования (по умолчанию CRITICAL — полная тишина)
        clear_handlers: очищать ли существующие хендлеры
        stop_propagation: останавливать ли всплытие логов в root
    """
    for name in names:
        logger_obj = logging.getLogger(name)
        logger_obj.setLevel(level)
        if clear_handlers:
            logger_obj.handlers.clear()
        if stop_propagation:
            logger_obj.propagate = False


mute_loggers(libs_to_mute)


load_dotenv()


def format_exception_with_filtered_traceback(
    exc_type,
    exc_value,
    exc_traceback,
    project_root: Path = None,
    max_frames: int = None,
) -> str:
    """
    Форматирует исключение с фильтрацией и красивым отображением трейсбека.
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent

    if max_frames is None:
        max_frames = int(os.environ.get("LOG_MAX_FRAMES", "10"))

    exclude_starts = {
        "venv",
        ".venv",
        "lib",
        "scripts",
        "include",
        "site-packages",
    }

    frames = traceback.extract_tb(exc_traceback)
    filtered_frames = []

    for frame in frames:
        file_path = Path(frame.filename)
        try:
            rel_path = file_path.relative_to(project_root)
            rel_str = str(rel_path).lower()
            first_part = (
                rel_str.split(os.sep)[0] if os.sep in rel_str else rel_str
            )
            if first_part in exclude_starts:
                continue
            filtered_frames.append(frame)
        except ValueError:
            continue

    if len(filtered_frames) > max_frames:
        filtered_frames = filtered_frames[-max_frames:]

    if not filtered_frames:
        formatted_exc = "".join(
            traceback.format_exception_only(exc_type, exc_value)
        ).rstrip()
        return f"{formatted_exc}"

    tb_lines = []
    arrow = ">"

    for i, frame in enumerate(filtered_frames):
        indent = "└" + "──" * i
        try:
            rel_file = Path(frame.filename).relative_to(project_root)
        except ValueError:
            rel_file = Path(frame.filename).name

        tb_lines.append(
            f"{indent}{arrow} File \"{rel_file}\", line {frame.lineno}, in {frame.name}: \t"
            f"[{frame.line.strip() if frame.line else ''}]"
        )

    formatted_exc = "".join(
        traceback.format_exception_only(exc_type, exc_value)
    ).rstrip()
    formatted_tb = "\n".join(tb_lines) + f"\n  {formatted_exc}"

    last = filtered_frames[-1]
    formatted_tb += f"- [{Path(last.filename).name}:{last.lineno}]"

    return formatted_tb


class InterceptHandler(logging.Handler):
    """
    Перехватывает стандартные логи Python и перенаправляет их в Loguru.
    Автоматически форматирует трейсбеки с фильтрацией.
    """

    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Получаем информацию о месте вызова из record
        frame = sys._getframe(1)  # Начинаем с текущего фрейма
        depth = 1
        # Пропускаем фреймы, связанные с logging и loguru
        while frame and (
            frame.f_code.co_filename == logging.__file__
            or "loguru" in frame.f_code.co_filename
        ):
            frame = frame.f_back
            depth += 1

        exc_info = record.exc_info
        if exc_info:
            exc_type, exc_value, exc_traceback = exc_info
            formatted_tb = format_exception_with_filtered_traceback(
                exc_type, exc_value, exc_traceback
            )
            message = f"{record.getMessage()}\n{formatted_tb}"
        else:
            message = record.getMessage()

        logger.opt(depth=depth).log(level, message)
        if record.levelno >= logging.CRITICAL:
            logger.error(
                "CRITICAL error detected — shutting down application."
            )
            logger.complete()
            time.sleep(0.1)
            sys.exit(1)


def setup_logging():
    """
    Настраивает систему логирования с автоматическим форматированием трейсбеков.
    """
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_file = os.environ.get("LOG_FILE", "app.log")
    log_to_console = os.environ.get("LOG_TO_CONSOLE", "true").lower() == "true"
    log_to_file = os.environ.get("LOG_TO_FILE", "true").lower() == "true"

    rotation = os.environ.get("LOG_ROTATION", "10 MB")
    retention = os.environ.get("LOG_RETENTION", "10 days")
    compression = os.environ.get("LOG_COMPRESSION", "zip")

    log_format = (
        "[<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green>] "
        "<level>{level: >8}</level> - <level><white>{message}</white></level> "
        "({file}:{line})"
    )

    # Настройка стандартного logging для перехвата
    logging.root.handlers = []
    logging.root.setLevel(logging.NOTSET)
    logging.basicConfig(handlers=[InterceptHandler()], level=0)

    # Очищаем существующие обработчики loguru
    logger.remove()

    # Консольный вывод
    if log_to_console:
        logger.add(
            sys.stderr,
            format=log_format,
            level=log_level,
            backtrace=False,  # Отключаем встроенный backtrace, так как используем кастомный
            diagnose=False,
            enqueue=True,
        )

    # Файловый вывод
    if log_to_file:
        logger.add(
            log_file,
            format=log_format,
            level=log_level,
            rotation=rotation,
            retention=retention,
            compression=compression,
            backtrace=False,
            diagnose=False,
            enqueue=True,
        )
