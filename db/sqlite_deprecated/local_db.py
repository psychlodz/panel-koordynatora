import sqlite3
import sys
from pathlib import Path

from config import app_dir


LOCAL_DB_FILENAME = "kompas.db"
SQL_DIRNAME = "db"


def local_db_path() -> Path:
    return Path(app_dir()) / LOCAL_DB_FILENAME


def create_local_connection() -> sqlite3.Connection:
    db_path = local_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _sql_resource_path(filename: str) -> Path:
    resource_root = Path(
        getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    )
    return resource_root / SQL_DIRNAME / filename


def _read_sql_script(filename: str) -> str:
    return _sql_resource_path(filename).read_text(encoding="utf-8")


def _database_is_empty(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        """
        SELECT COUNT(*)
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        """
    ).fetchone()
    return row[0] == 0


def _ensure_episode_source_columns(connection: sqlite3.Connection) -> None:
    rows = connection.execute("PRAGMA table_info(pk_epizody)").fetchall()
    columns = {row["name"] for row in rows}
    additions = {
        "source_system": "TEXT",
        "source_type": "TEXT",
        "source_id": "TEXT",
    }
    with connection:
        for column_name, column_type in additions.items():
            if column_name not in columns:
                connection.execute(
                    f"""
                    ALTER TABLE pk_epizody
                    ADD COLUMN {column_name} {column_type}
                    """
                )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            uq_pk_epizody_source
            ON pk_epizody(source_system, source_type, source_id)
            WHERE source_system IS NOT NULL
              AND source_type IS NOT NULL
              AND source_id IS NOT NULL
            """
        )


def initialize_local_db() -> Path:
    connection = create_local_connection()
    try:
        database_was_empty = _database_is_empty(connection)
        try:
            connection.executescript(
                "BEGIN;\n"
                + _read_sql_script("schema.sql")
                + "\nCOMMIT;"
            )
        except Exception:
            connection.rollback()
            raise

        _ensure_episode_source_columns(connection)

        scripts = []
        if database_was_empty:
            scripts.append(_read_sql_script("seed.sql"))
        scripts.append(_read_sql_script("migrations.sql"))

        initialization_script = (
            "BEGIN;\n"
            + "\n".join(scripts)
            + "\nCOMMIT;"
        )
        try:
            connection.executescript(initialization_script)
        except Exception:
            connection.rollback()
            raise
    finally:
        connection.close()

    return local_db_path()
