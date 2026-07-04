from contextlib import closing

from local_db import create_local_connection, initialize_local_db


def _unit_id(jo_id):
    value = "" if jo_id is None else str(jo_id).strip()
    if not value:
        raise ValueError("Identyfikator jednostki jest wymagany")
    return value


def _optional_text(value):
    text = str(value or "").strip()
    return text or None


def list_program_units(program_id) -> list[dict]:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        rows = connection.execute(
            """
            SELECT
                program_id,
                jo_id,
                jo_symbol,
                jo_nazwa,
                created_at
            FROM pk_program_units
            WHERE program_id = ?
            ORDER BY jo_symbol COLLATE NOCASE,
                     jo_nazwa COLLATE NOCASE,
                     jo_id
            """,
            (program_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def assign_unit_to_program(
    program_id,
    jo_id,
    jo_symbol,
    jo_nazwa,
) -> None:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO pk_program_units(
                    program_id,
                    jo_id,
                    jo_symbol,
                    jo_nazwa
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(program_id, jo_id) DO UPDATE SET
                    jo_symbol = excluded.jo_symbol,
                    jo_nazwa = excluded.jo_nazwa
                """,
                (
                    program_id,
                    _unit_id(jo_id),
                    _optional_text(jo_symbol),
                    _optional_text(jo_nazwa),
                ),
            )


def remove_unit_from_program(program_id, jo_id) -> None:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        with connection:
            cursor = connection.execute(
                """
                DELETE FROM pk_program_units
                WHERE program_id = ?
                  AND jo_id = ?
                """,
                (program_id, _unit_id(jo_id)),
            )
            if cursor.rowcount == 0:
                raise ValueError("Jednostka nie była przypisana programowi")
