import logging
import os
from pathlib import Path

from config import app_dir


DEBUG_ENVIRONMENT_VARIABLE = "KOMPAS_DEBUG"
DEBUG_LOG_FILENAME = "kompas_debug.log"
DEBUG_LOGGERS = (
    "episode_generator",
    "app.repositories.qualification_repository",
    "app.ui.qualification_visits_window",
)


def configure_debug_logging():
    """Włącza diagnostykę kwalifikacji wyłącznie w trybie DEBUG."""
    enabled = os.getenv(
        DEBUG_ENVIRONMENT_VARIABLE, ""
    ).strip().lower() in {"1", "true", "yes", "tak"}
    if not enabled:
        return None

    logs_directory = Path(app_dir()) / "logs"
    logs_directory.mkdir(parents=True, exist_ok=True)
    log_path = logs_directory / DEBUG_LOG_FILENAME
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        )
    )

    for logger_name in DEBUG_LOGGERS:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        logger.propagate = False
    return log_path


__all__ = [
    "DEBUG_ENVIRONMENT_VARIABLE",
    "DEBUG_LOG_FILENAME",
    "configure_debug_logging",
]
