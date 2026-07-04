import configparser
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from config import app_dir
from local_db import create_local_connection


CONFIG_SECTION = "kompas_database"
SUPPORTED_ENGINES = {"sqlite", "postgres"}


@dataclass(frozen=True)
class DatabaseSettings:
    engine: str = "sqlite"
    sqlite_path: str | None = None
    postgres_dsn: str | None = None


def load_database_settings(config_path=None) -> DatabaseSettings:
    path = Path(config_path or Path(app_dir()) / "config.ini")
    parser = configparser.ConfigParser()
    if path.exists():
        parser.read(path, encoding="utf-8")

    engine = parser.get(
        CONFIG_SECTION,
        "engine",
        fallback="sqlite",
    ).strip().lower()
    if engine not in SUPPORTED_ENGINES:
        raise ValueError(
            "Nieobsługiwany silnik bazy KOMPAS: "
            f"{engine}. Dozwolone: sqlite, postgres"
        )

    sqlite_path = parser.get(
        CONFIG_SECTION,
        "sqlite_path",
        fallback="",
    ).strip() or None
    postgres_dsn = (
        os.environ.get("KOMPAS_POSTGRES_DSN", "").strip()
        or parser.get(
            CONFIG_SECTION,
            "postgres_dsn",
            fallback="",
        ).strip()
        or None
    )
    return DatabaseSettings(
        engine=engine,
        sqlite_path=sqlite_path,
        postgres_dsn=postgres_dsn,
    )


def _create_sqlite_connection(settings):
    if not settings.sqlite_path:
        return create_local_connection()

    path = Path(settings.sqlite_path)
    if not path.is_absolute():
        path = Path(app_dir()) / path
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _create_postgres_connection(settings):
    if not settings.postgres_dsn:
        raise ValueError(
            "Brak postgres_dsn w sekcji [kompas_database] "
            "lub zmiennej KOMPAS_POSTGRES_DSN"
        )
    data_key = os.environ.get("KOMPAS_DATA_KEY", "")
    if not data_key:
        raise ValueError(
            "Brak zmiennej środowiskowej KOMPAS_DATA_KEY"
        )

    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(
            "Obsługa PostgreSQL wymaga pakietu psycopg[binary]"
        ) from exc

    connection = psycopg.connect(settings.postgres_dsn)
    try:
        connection.execute(
            "SELECT set_config('kompas.data_key', %s, false)",
            (data_key,),
        )
        # Utrwal ustawienie sesyjne poza transakcją otwieraną przez psycopg.
        connection.commit()
    except Exception:
        connection.close()
        raise
    return connection


def create_connection(settings=None):
    """Tworzy połączenie z bazą danych KOMPAS, nie z Oracle."""
    settings = settings or load_database_settings()
    if settings.engine == "sqlite":
        return _create_sqlite_connection(settings)
    return _create_postgres_connection(settings)


@contextmanager
def database_connection(settings=None):
    connection = create_connection(settings)
    try:
        yield connection
    finally:
        connection.close()
