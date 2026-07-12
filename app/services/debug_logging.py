import logging
import os
from pathlib import Path

from config import app_dir


DEBUG_ENVIRONMENT_VARIABLE = "KOMPAS_DEBUG"
DEBUG_LOG_FILENAME = "kompas_debug.log"
APP_LOG_FILENAME = "kompas.log"
DEBUG_LOGGERS = (
    "episode_generator",
    "app.repositories.qualification_repository",
    "app.ui.qualification_visits_window",
)
APP_LOGGERS = (
    "app",
    "episode_generator",
    "pathway_service",
)


def _logs_directory():
    logs_directory = Path(app_dir()) / "logs"
    logs_directory.mkdir(parents=True, exist_ok=True)
    return logs_directory


def application_log_path():
    return _logs_directory() / APP_LOG_FILENAME


def _add_file_handler(logger, log_path, level):
    resolved = str(log_path)
    for handler in logger.handlers:
        if (
            isinstance(handler, logging.FileHandler)
            and getattr(handler, "baseFilename", None) == resolved
        ):
            return
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        )
    )
    logger.addHandler(handler)


def configure_application_logging():
    """Tworzy standardowy katalog logów i plik logu aplikacji."""
    log_path = application_log_path()
    for logger_name in APP_LOGGERS:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        _add_file_handler(logger, log_path, logging.INFO)
    return log_path


def configure_debug_logging():
    """Włącza diagnostykę kwalifikacji wyłącznie w trybie DEBUG."""
    configure_application_logging()
    enabled = os.getenv(
        DEBUG_ENVIRONMENT_VARIABLE, ""
    ).strip().lower() in {"1", "true", "yes", "tak"}
    if not enabled:
        return None

    log_path = _logs_directory() / DEBUG_LOG_FILENAME

    for logger_name in DEBUG_LOGGERS:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        _add_file_handler(logger, log_path, logging.DEBUG)
        logger.propagate = False
    return log_path


__all__ = [
    "APP_LOG_FILENAME",
    "DEBUG_ENVIRONMENT_VARIABLE",
    "DEBUG_LOG_FILENAME",
    "application_log_path",
    "configure_application_logging",
    "configure_debug_logging",
]
