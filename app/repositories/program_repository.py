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


def _unit_value(unit, field_name):
    if isinstance(unit, dict):
        return unit.get(field_name)
    return getattr(unit, field_name, None)


def _normalized_units(units):
    result = []
    seen = set()
    for unit in units or []:
        jo_id = str(_unit_value(unit, "jo_id") or "").strip()
        if not jo_id or jo_id in seen:
            continue
        seen.add(jo_id)
        result.append(
            (
                jo_id,
                _optional_text(_unit_value(unit, "jo_symbol")),
                _optional_text(_unit_value(unit, "jo_nazwa")),
            )
        )
    return result


def _replace_program_units(connection, program_id, units):
    normalized = _normalized_units(units)
    connection.execute(
        "DELETE FROM pk_program_units WHERE program_id = ?",
        (program_id,),
    )
    if normalized:
        connection.executemany(
            """
            INSERT INTO pk_program_units(
                program_id,
                jo_id,
                jo_symbol,
                jo_nazwa
            )
            VALUES (?, ?, ?, ?)
            """,
            [
                (program_id, jo_id, symbol, name)
                for jo_id, symbol, name in normalized
            ],
        )


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
        unit_rows = connection.execute(
            """
            SELECT program_id, jo_id, jo_symbol
            FROM pk_program_units
            ORDER BY jo_symbol COLLATE NOCASE, jo_id
            """
        ).fetchall()
    symbols = {}
    for unit in unit_rows:
        symbols.setdefault(unit["program_id"], []).append(
            unit["jo_symbol"] or unit["jo_id"]
        )
    result = [dict(row) for row in rows]
    for program in result:
        program["jednostki"] = ", ".join(
            symbols.get(program["program_id"], [])
        )
    return result


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


def create_program(
    kod,
    nazwa,
    wersja=None,
    opis=None,
    units=None,
) -> int:
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
            if units is not None:
                _replace_program_units(connection, program_id, units)

    return int(program_id)


def update_program(
    program_id,
    kod,
    nazwa,
    wersja=None,
    opis=None,
    czy_aktywny=1,
    units=None,
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
            if units is not None:
                _replace_program_units(connection, program_id, units)

    return int(program_id)
