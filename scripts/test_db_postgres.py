import os
import sys
import types
import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.repositories import db_connection
from app.repositories.db_connection import (
    DatabaseSettings,
    POSTGRES_CONNECTION_ERROR,
    create_connection,
    initialize_database,
)


class FakeCursor:
    def __init__(self, rows=None, rowcount=1):
        self.rows = list(rows or [])
        self.rowcount = rowcount

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def fetchall(self):
        result = self.rows
        self.rows = []
        return result

    def executemany(self, sql, parameters):
        self.executemany_call = (sql, list(parameters))


class FakePostgresConnection:
    def __init__(self):
        self.calls = []
        self.closed = False

    def execute(self, sql, parameters=()):
        self.calls.append((sql, parameters))
        if "RETURNING program_id" in sql:
            return FakeCursor([{"program_id": 41}])
        return FakeCursor([])

    def executemany(self, sql, parameters):
        self.calls.append((sql, list(parameters)))
        return FakeCursor([])

    def cursor(self):
        cursor = FakeCursor([])
        self.last_cursor = cursor
        return cursor

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        self.closed = True


def test_compatibility_layer():
    fake = FakePostgresConnection()
    psycopg = types.ModuleType("psycopg")
    psycopg.connect = lambda dsn, row_factory=None: fake
    rows = types.ModuleType("psycopg.rows")
    rows.dict_row = object()
    sys.modules["psycopg"] = psycopg
    sys.modules["psycopg.rows"] = rows

    connection = create_connection(
        DatabaseSettings(
            engine="postgres",
            postgres_dsn="host=fake dbname=kompas",
        )
    )
    cursor = connection.execute(
        """
        INSERT INTO pk_programy(kod, nazwa)
        VALUES (?, ?)
        """,
        ("TEST", "Program testowy"),
    )
    assert cursor.lastrowid == 41
    assert "%s" in fake.calls[-1][0]
    assert "RETURNING program_id" in fake.calls[-1][0]

    connection.execute(
        """
        SELECT login
        FROM pk_users
        WHERE login = ? COLLATE NOCASE
        """,
        ("admin",),
    )
    assert "LOWER(login) = LOWER(%s)" in fake.calls[-1][0]
    assert "COLLATE NOCASE" not in fake.calls[-1][0]
    connection.execute(
        """
        SELECT COALESCE(GROUP_CONCAT(r.code, ', '), '') AS roles
        FROM pk_roles r
        """
    )
    assert "STRING_AGG(r.code, ', ')" in fake.calls[-1][0]
    connection.executemany(
        """
        INSERT INTO pk_user_roles(user_id, role_id)
        VALUES (?, ?)
        """,
        [(1, 1), (1, 2)],
    )
    assert "%s" in fake.last_cursor.executemany_call[0]

    original_loader = db_connection.load_database_settings
    db_connection.load_database_settings = lambda: DatabaseSettings(
        engine="postgres",
        postgres_dsn="host=fake dbname=kompas",
    )
    try:
        assert (
            db_connection.patient_id_column("e")
            == "e.pacjent_id_eskulap"
        )
    finally:
        db_connection.load_database_settings = original_loader
    connection.close()


def test_non_postgres_engine_is_rejected():
    try:
        initialize_database(DatabaseSettings(engine="legacy"))
    except ValueError as exc:
        assert "Obsługiwany jest wyłącznie PostgreSQL" in str(exc)
    else:
        raise AssertionError("Nieobsługiwany silnik bazy nie został odrzucony.")


def test_missing_postgres_dsn_is_rejected():
    try:
        initialize_database(DatabaseSettings(engine="postgres"))
    except ValueError as exc:
        assert str(exc) == POSTGRES_CONNECTION_ERROR
    else:
        raise AssertionError("Brak DSN PostgreSQL nie został odrzucony.")


def test_live_postgres(dsn):
    sys.modules.pop("psycopg", None)
    sys.modules.pop("psycopg.rows", None)
    connection = create_connection(
        DatabaseSettings(engine="postgres", postgres_dsn=dsn)
    )
    code = f"DBPG2_{uuid.uuid4().hex[:12].upper()}"
    try:
        cursor = connection.execute(
            """
            INSERT INTO pk_programy(kod, nazwa, opis)
            VALUES (?, ?, ?)
            """,
            (code, "Test DB-PG-2", "Rekord testowy do wycofania"),
        )
        program_id = cursor.lastrowid
        row = connection.execute(
            """
            SELECT program_id, kod
            FROM pk_programy
            WHERE program_id = ?
            """,
            (program_id,),
        ).fetchone()
        assert row["kod"] == code
    finally:
        connection.rollback()
        connection.close()


def main():
    test_non_postgres_engine_is_rejected()
    print("Walidacja silnika bazy: OK")

    test_missing_postgres_dsn_is_rejected()
    print("Walidacja konfiguracji PostgreSQL: OK")

    test_compatibility_layer()
    print("Warstwa zgodności PostgreSQL: OK")

    dsn = os.environ.get("KOMPAS_TEST_POSTGRES_DSN", "").strip()
    if dsn:
        test_live_postgres(dsn)
        print("Połączenie z testowym PostgreSQL: OK")
    else:
        print(
            "Test serwera pominięty. Ustaw KOMPAS_TEST_POSTGRES_DSN, "
            "aby uruchomić test integracyjny."
        )


if __name__ == "__main__":
    main()
