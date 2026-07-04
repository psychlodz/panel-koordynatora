from contextlib import closing

from app.repositories.db_connection import (
    create_connection as create_local_connection,
    initialize_database as initialize_local_db,
)


PROGRAM_COLUMNS = """
    program_id,
    kod,
    nazwa,
    wersja,
    opis,
    czy_aktywny,
    data_od,
    data_do,
    created_at,
    updated_at
"""


def _required_text(value, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"Pole {field_name} jest wymagane")
    return text


def _optional_text(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def list_programs() -> list[dict]:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        rows = connection.execute(
            f"""
            SELECT {PROGRAM_COLUMNS}
            FROM pk_programy
            ORDER BY czy_aktywny DESC, kod COLLATE NOCASE
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_program(program_id):
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        row = connection.execute(
            f"""
            SELECT {PROGRAM_COLUMNS}
            FROM pk_programy
            WHERE program_id = ?
            """,
            (program_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def create_program(kod, nazwa, wersja=None, opis=None) -> int:
    kod = _required_text(kod, "kod")
    nazwa = _required_text(nazwa, "nazwa")
    initialize_local_db()

    with closing(create_local_connection()) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO pk_programy(kod, nazwa, wersja, opis)
                VALUES (?, ?, ?, ?)
                """,
                (kod, nazwa, _optional_text(wersja), _optional_text(opis)),
            )
            program_id = cursor.lastrowid

    return int(program_id)


def update_program(
    program_id,
    kod,
    nazwa,
    wersja=None,
    opis=None,
    czy_aktywny=1,
) -> int:
    kod = _required_text(kod, "kod")
    nazwa = _required_text(nazwa, "nazwa")
    active = 1 if czy_aktywny else 0
    initialize_local_db()

    with closing(create_local_connection()) as connection:
        with connection:
            cursor = connection.execute(
                """
                UPDATE pk_programy
                SET kod = ?,
                    nazwa = ?,
                    wersja = ?,
                    opis = ?,
                    czy_aktywny = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE program_id = ?
                """,
                (
                    kod,
                    nazwa,
                    _optional_text(wersja),
                    _optional_text(opis),
                    active,
                    program_id,
                ),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Nie znaleziono programu o ID {program_id}")

    return int(program_id)
