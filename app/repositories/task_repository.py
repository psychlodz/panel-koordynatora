from contextlib import closing
from datetime import date, datetime

from app.repositories.db_connection import (
    create_connection,
    initialize_database,
    patient_id_column,
)


TERMINAL_STATUSES = ("ZAKONCZONE", "ZREALIZOWANE", "ANULOWANE")


def _active_status_clause(alias=None):
    placeholders = ", ".join("?" for _ in TERMINAL_STATUSES)
    prefix = f"{alias}." if alias else ""
    return f"UPPER({prefix}status) NOT IN ({placeholders})"


def list_active_tasks() -> list[dict]:
    initialize_database()
    with closing(create_connection()) as connection:
        rows = connection.execute(
            f"""
            SELECT
                z.zadanie_id,
                z.epizod_id,
                z.element_id,
                z.epizod_element_id,
                z.status,
                z.data_wymagana_do,
                z.data_zaplanowana,
                z.data_realizacji,
                z.zrodlo,
                z.eskulap_system,
                z.eskulap_id,
                z.eskulap_pracownik,
                z.eskulap_data_wizyty,
                z.eskulap_rodzaj_wizyty,
                z.eskulap_decyzja,
                z.uwagi,
                z.created_at,
                {patient_id_column("ep")} AS pacjent_id,
                ep.data_start,
                ep.koordynator_id,
                ep.program_id,
                ep.sciezka_id,
                p.kod AS program_kod,
                p.nazwa AS program_nazwa,
                s.kod AS sciezka_kod,
                s.nazwa AS sciezka_nazwa,
                COALESCE(ee.lp, e.lp) AS lp,
                COALESCE(ee.nazwa, e.nazwa_w_sciezce) AS nazwa_w_sciezce,
                k.kod AS klocek_kod,
                k.nazwa AS klocek_nazwa
            FROM pk_zadania z
            JOIN pk_epizody ep ON ep.epizod_id = z.epizod_id
            LEFT JOIN pk_programy p ON p.program_id = ep.program_id
            LEFT JOIN pk_sciezki s ON s.sciezka_id = ep.sciezka_id
            LEFT JOIN pk_epizod_elementy ee
                ON ee.epizod_element_id = z.epizod_element_id
            LEFT JOIN pk_sciezka_elementy e
                ON e.element_id = z.element_id
            LEFT JOIN pk_klocki k
                ON k.klocek_id = COALESCE(ee.klocek_id, e.klocek_id)
            WHERE {_active_status_clause("z")}
              AND ep.data_zakonczenia IS NULL
            ORDER BY
                COALESCE(z.data_zaplanowana, z.data_wymagana_do) IS NULL,
                COALESCE(z.data_zaplanowana, z.data_wymagana_do),
                ep.epizod_id,
                COALESCE(ee.lp, e.lp)
            """,
            TERMINAL_STATUSES,
        ).fetchall()
    return [dict(row) for row in rows]


def list_synchronized_event_keys() -> set[tuple[str, str]]:
    initialize_database()
    with closing(create_connection()) as connection:
        rows = connection.execute(
            """
            SELECT eskulap_system, eskulap_id
            FROM pk_zadania
            WHERE eskulap_system IS NOT NULL
              AND eskulap_id IS NOT NULL
            """
        ).fetchall()
    return {
        (str(row["eskulap_system"]), str(row["eskulap_id"]))
        for row in rows
    }


def _scheduled_value(value) -> str:
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time()).isoformat(
            timespec="seconds"
        )
    text = str(value or "").strip()
    if not text:
        raise ValueError("Termin zaplanowania jest wymagany")
    return text


def schedule_task(zadanie_id, planned_at, uwagi=None) -> None:
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            cursor = connection.execute(
                f"""
                UPDATE pk_zadania
                SET status = 'ZAPLANOWANO',
                    data_zaplanowana = ?,
                    uwagi = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE zadanie_id = ?
                  AND {_active_status_clause()}
                """,
                (
                    _scheduled_value(planned_at),
                    str(uwagi).strip() if uwagi else None,
                    zadanie_id,
                    *TERMINAL_STATUSES,
                ),
            )
            if cursor.rowcount == 0:
                raise ValueError(
                    "Nie znaleziono aktywnego zadania do zaplanowania"
                )


def cancel_task(zadanie_id) -> None:
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            cursor = connection.execute(
                f"""
                UPDATE pk_zadania
                SET status = 'ANULOWANE',
                    updated_at = CURRENT_TIMESTAMP
                WHERE zadanie_id = ?
                  AND {_active_status_clause()}
                """,
                (zadanie_id, *TERMINAL_STATUSES),
            )
            if cursor.rowcount == 0:
                raise ValueError(
                    "Nie znaleziono aktywnego zadania do anulowania"
                )
