import configparser
import os
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from config import app_dir
from local_db import (
    create_local_connection,
    initialize_local_db,
    local_db_path,
)


CONFIG_SECTION = "kompas_database"
SUPPORTED_ENGINES = {"sqlite", "postgres"}
INSERT_IDS = {
    "pk_users": "user_id",
    "pk_roles": "role_id",
    "pk_programy": "program_id",
    "pk_sciezki": "sciezka_id",
    "pk_typy_elementow": "typ_id",
    "pk_grupy_klockow": "grupa_id",
    "pk_jednostki_czasu": "jednostka_czasu_id",
    "pk_klocki": "klocek_id",
    "pk_sciezka_elementy": "element_id",
    "pk_sciezka_zaleznosci": "zaleznosc_id",
    "pk_wyzwalacze": "trigger_id",
    "pk_epizody": "epizod_id",
    "pk_zadania": "zadanie_id",
}


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

    path = _sqlite_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _sqlite_path(settings):
    path = Path(settings.sqlite_path or local_db_path())
    if not path.is_absolute():
        path = Path(app_dir()) / path
    return path.resolve()


def _create_postgres_connection(settings):
    if not settings.postgres_dsn:
        raise ValueError(
            "Brak postgres_dsn w sekcji [kompas_database] "
            "lub zmiennej KOMPAS_POSTGRES_DSN"
        )
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError(
            "Obsługa PostgreSQL wymaga pakietu psycopg[binary]"
        ) from exc

    return psycopg.connect(
        settings.postgres_dsn,
        row_factory=dict_row,
    )


def _replace_qmark_placeholders(sql):
    result = []
    quote = None
    index = 0
    while index < len(sql):
        character = sql[index]
        if quote:
            result.append(character)
            if character == quote:
                if index + 1 < len(sql) and sql[index + 1] == quote:
                    result.append(sql[index + 1])
                    index += 1
                else:
                    quote = None
        elif character in ("'", '"'):
            quote = character
            result.append(character)
        elif character == "?":
            result.append("%s")
        else:
            result.append(character)
        index += 1
    return "".join(result)


def _postgres_sql(sql):
    translated = _replace_qmark_placeholders(sql)
    translated = re.sub(
        r"(?P<left>\b[\w.]+)\s*=\s*"
        r"(?P<right>%s|'(?:''|[^'])*')\s+COLLATE\s+NOCASE",
        r"LOWER(\g<left>) = LOWER(\g<right>)",
        translated,
        flags=re.IGNORECASE,
    )
    translated = re.sub(
        r"\s+COLLATE\s+NOCASE\b",
        "",
        translated,
        flags=re.IGNORECASE,
    )
    translated = re.sub(
        r"GROUP_CONCAT\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)",
        r"STRING_AGG(\1, \2)",
        translated,
        flags=re.IGNORECASE,
    )
    if translated.strip().upper() == "BEGIN IMMEDIATE":
        return "BEGIN"
    return translated


def _insert_id_column(sql):
    match = re.match(
        r"\s*INSERT\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*)",
        sql,
        flags=re.IGNORECASE,
    )
    if not match or re.search(r"\bRETURNING\b", sql, re.IGNORECASE):
        return None
    return INSERT_IDS.get(match.group(1).lower())


class DatabaseCursor:
    def __init__(self, cursor, lastrowid=None):
        self._cursor = cursor
        self._lastrowid = lastrowid

    @property
    def lastrowid(self):
        if self._lastrowid is not None:
            return self._lastrowid
        return getattr(self._cursor, "lastrowid", None)

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def fetchone(self):
        return _compatible_row(self._cursor.fetchone())

    def fetchall(self):
        return [
            _compatible_row(row)
            for row in self._cursor.fetchall()
        ]

    def __iter__(self):
        return (
            _compatible_row(row)
            for row in self._cursor
        )

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class DatabaseRow(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return tuple(self.values())[key]
        return super().__getitem__(key)


def _compatible_row(row):
    if isinstance(row, dict) and not isinstance(row, DatabaseRow):
        return DatabaseRow(row)
    return row


class DatabaseConnection:
    def __init__(self, connection, engine):
        self._connection = connection
        self.engine = engine

    def _sql(self, sql):
        return _postgres_sql(sql) if self.engine == "postgres" else sql

    def execute(self, sql, parameters=None):
        parameters = () if parameters is None else parameters
        translated = self._sql(sql)
        id_column = (
            _insert_id_column(translated)
            if self.engine == "postgres"
            else None
        )
        if id_column:
            translated = f"{translated.rstrip().rstrip(';')} RETURNING {id_column}"
        cursor = self._connection.execute(translated, parameters)
        lastrowid = None
        if id_column:
            row = cursor.fetchone()
            lastrowid = row[id_column]
        return DatabaseCursor(cursor, lastrowid)

    def executemany(self, sql, parameters):
        if self.engine == "postgres":
            cursor = self._connection.cursor()
            cursor.executemany(self._sql(sql), parameters)
        else:
            cursor = self._connection.executemany(
                self._sql(sql),
                parameters,
            )
        return DatabaseCursor(cursor)

    def commit(self):
        return self._connection.commit()

    def rollback(self):
        return self._connection.rollback()

    def close(self):
        return self._connection.close()

    def __enter__(self):
        self._connection.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self._connection.__exit__(
            exc_type,
            exc_value,
            traceback,
        )

    def __getattr__(self, name):
        return getattr(self._connection, name)


def initialize_database(settings=None):
    """Inicjalizuje automatycznie wyłącznie developerską bazę SQLite."""
    settings = settings or load_database_settings()
    if settings.engine != "sqlite":
        return None
    if _sqlite_path(settings) == Path(local_db_path()).resolve():
        return initialize_local_db()

    database_path = _sqlite_path(settings)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        empty = connection.execute(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            """
        ).fetchone()[0] == 0
        sql_root = Path(app_dir()) / "db"
        scripts = [
            (sql_root / "schema.sql").read_text(encoding="utf-8"),
        ]
        if empty:
            scripts.append(
                (sql_root / "seed.sql").read_text(encoding="utf-8")
            )
        scripts.append(
            (sql_root / "migrations.sql").read_text(encoding="utf-8")
        )
        connection.executescript("\n".join(scripts))
    finally:
        connection.close()
    return database_path


def create_connection(settings=None):
    """Tworzy ujednolicone połączenie z bazą KOMPAS, nigdy z Oracle."""
    settings = settings or load_database_settings()
    raw_connection = (
        _create_sqlite_connection(settings)
        if settings.engine == "sqlite"
        else _create_postgres_connection(settings)
    )
    return DatabaseConnection(raw_connection, settings.engine)


def patient_id_column(alias=None):
    settings = load_database_settings()
    column = (
        "pacjent_id"
        if settings.engine == "sqlite"
        else "pacjent_id_eskulap"
    )
    return f"{alias}.{column}" if alias else column


def is_integrity_error(error):
    if isinstance(error, sqlite3.IntegrityError):
        return True
    error_type = type(error)
    return (
        error_type.__module__.startswith("psycopg")
        and error_type.__name__ in {
            "IntegrityError",
            "UniqueViolation",
            "ForeignKeyViolation",
            "CheckViolation",
            "NotNullViolation",
        }
    )


@contextmanager
def database_connection(settings=None):
    connection = create_connection(settings)
    try:
        yield connection
    finally:
        connection.close()
