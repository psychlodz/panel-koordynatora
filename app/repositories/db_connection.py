import configparser
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from config import app_dir


CONFIG_SECTION = "kompas_db"
LEGACY_CONFIG_SECTION = "kompas_database"
SUPPORTED_ENGINE = "postgres"
POSTGRES_CONNECTION_ERROR = (
    "Brak połączenia z centralną bazą KOMPAS PostgreSQL. "
    "Sprawdź konfigurację."
)
SQLITE_UNSUPPORTED_ERROR = (
    "SQLite nie jest już wspierany. Skonfiguruj PostgreSQL."
)
INSERT_IDS = {
    "pk_users": "user_id",
    "pk_roles": "role_id",
    "pk_programy": "program_id",
    "pk_sciezki": "sciezka_id",
    "pk_typy_elementow": "typ_id",
    "pk_grupy_klockow": "grupa_id",
    "pk_jednostki_czasu": "jednostka_czasu_id",
    "pk_klocki": "klocek_id",
    "pk_mapowanie_wizyt": "mapowanie_id",
    "pk_sciezka_elementy": "element_id",
    "pk_sciezka_zaleznosci": "zaleznosc_id",
    "pk_wyzwalacze": "trigger_id",
    "pk_epizody": "epizod_id",
    "pk_zadania": "zadanie_id",
}


@dataclass(frozen=True)
class DatabaseSettings:
    engine: str = SUPPORTED_ENGINE
    postgres_dsn: str | None = None


def _config_section(parser):
    if parser.has_section(CONFIG_SECTION):
        return CONFIG_SECTION
    if parser.has_section(LEGACY_CONFIG_SECTION):
        return LEGACY_CONFIG_SECTION
    return CONFIG_SECTION


def _validate_settings(settings):
    engine = str(settings.engine or "").strip().lower()
    if engine == "sqlite":
        raise ValueError(SQLITE_UNSUPPORTED_ERROR)
    if engine != SUPPORTED_ENGINE:
        raise ValueError(
            f"Nieobsługiwany silnik bazy KOMPAS: {engine or 'brak'}. "
            "Skonfiguruj PostgreSQL."
        )
    if not str(settings.postgres_dsn or "").strip():
        raise ValueError(POSTGRES_CONNECTION_ERROR)


def load_database_settings(config_path=None) -> DatabaseSettings:
    path = Path(config_path or Path(app_dir()) / "config.ini")
    parser = configparser.ConfigParser()
    if path.exists():
        parser.read(path, encoding="utf-8")

    section = _config_section(parser)
    engine = parser.get(
        section,
        "engine",
        fallback=SUPPORTED_ENGINE,
    ).strip().lower()
    postgres_dsn = (
        os.environ.get("KOMPAS_POSTGRES_DSN", "").strip()
        or parser.get(
            section,
            "postgres_dsn",
            fallback="",
        ).strip()
        or None
    )
    settings = DatabaseSettings(
        engine=engine,
        postgres_dsn=postgres_dsn,
    )
    _validate_settings(settings)
    return settings


def _create_postgres_connection(settings):
    _validate_settings(settings)
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError(
            f"{POSTGRES_CONNECTION_ERROR} "
            "Brak sterownika psycopg[binary]."
        ) from exc

    try:
        return psycopg.connect(
            settings.postgres_dsn,
            row_factory=dict_row,
        )
    except Exception as exc:
        raise ConnectionError(POSTGRES_CONNECTION_ERROR) from exc


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
        return self._lastrowid

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
    engine = SUPPORTED_ENGINE

    def __init__(self, connection):
        self._connection = connection

    def execute(self, sql, parameters=None):
        parameters = () if parameters is None else parameters
        translated = _postgres_sql(sql)
        id_column = _insert_id_column(translated)
        if id_column:
            translated = (
                f"{translated.rstrip().rstrip(';')} "
                f"RETURNING {id_column}"
            )
        cursor = self._connection.execute(translated, parameters)
        lastrowid = None
        if id_column:
            row = cursor.fetchone()
            lastrowid = row[id_column]
        return DatabaseCursor(cursor, lastrowid)

    def executemany(self, sql, parameters):
        cursor = self._connection.cursor()
        cursor.executemany(_postgres_sql(sql), parameters)
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
    """Waliduje konfigurację centralnej bazy; nie tworzy lokalnej bazy."""
    settings = settings or load_database_settings()
    _validate_settings(settings)
    return None


def create_connection(settings=None):
    """Tworzy połączenie wyłącznie z centralną bazą KOMPAS PostgreSQL."""
    settings = settings or load_database_settings()
    return DatabaseConnection(_create_postgres_connection(settings))


def patient_id_column(alias=None):
    column = "pacjent_id_eskulap"
    return f"{alias}.{column}" if alias else column


def is_integrity_error(error):
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


__all__ = [
    "CONFIG_SECTION",
    "DatabaseConnection",
    "DatabaseSettings",
    "POSTGRES_CONNECTION_ERROR",
    "SQLITE_UNSUPPORTED_ERROR",
    "create_connection",
    "database_connection",
    "initialize_database",
    "is_integrity_error",
    "load_database_settings",
    "patient_id_column",
]
