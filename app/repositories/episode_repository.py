from contextlib import closing

from app.repositories.db_connection import (
    create_connection,
    initialize_database,
    patient_id_column,
)


def _episode_columns():
    return f"""
        e.epizod_id,
        {patient_id_column("e")} AS pacjent_id,
        e.program_id,
        e.sciezka_id,
        e.data_start,
        e.data_zakonczenia,
        e.status,
        e.koordynator_id,
        e.uwagi,
        e.source_system,
        e.source_type,
        e.source_id,
        e.created_at,
        e.updated_at,
        p.kod AS program_kod,
        p.nazwa AS program_nazwa,
        s.kod AS sciezka_kod,
        s.nazwa AS sciezka_nazwa
    """


def list_episodes() -> list[dict]:
    initialize_database()
    with closing(create_connection()) as connection:
        rows = connection.execute(
            f"""
            SELECT
                {_episode_columns()},
                COALESCE(t.liczba_zadan, 0) AS liczba_zadan,
                COALESCE(
                    t.liczba_zrealizowanych_zadan, 0
                ) AS liczba_zrealizowanych_zadan,
                CASE
                    WHEN COALESCE(t.liczba_zadan, 0) = 0 THEN 0
                    ELSE ROUND(
                        100.0 * t.liczba_zrealizowanych_zadan
                        / t.liczba_zadan,
                        1
                    )
                END AS procent_realizacji
            FROM pk_epizody e
            LEFT JOIN pk_programy p ON p.program_id = e.program_id
            LEFT JOIN pk_sciezki s ON s.sciezka_id = e.sciezka_id
            LEFT JOIN (
                SELECT
                    epizod_id,
                    COUNT(*) AS liczba_zadan,
                    SUM(
                        CASE
                            WHEN UPPER(status) IN (
                                'ZAKONCZONE',
                                'ZREALIZOWANO',
                                'ZREALIZOWANE'
                            )
                            THEN 1
                            ELSE 0
                        END
                    ) AS liczba_zrealizowanych_zadan
                FROM pk_zadania
                GROUP BY epizod_id
            ) t ON t.epizod_id = e.epizod_id
            ORDER BY e.data_start DESC, e.epizod_id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def list_active_episodes() -> list[dict]:
    initialize_database()
    with closing(create_connection()) as connection:
        rows = connection.execute(
            f"""
            SELECT {_episode_columns()}
            FROM pk_epizody e
            LEFT JOIN pk_programy p ON p.program_id = e.program_id
            LEFT JOIN pk_sciezki s ON s.sciezka_id = e.sciezka_id
            WHERE e.data_zakonczenia IS NULL
            ORDER BY e.data_start DESC, e.epizod_id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_episode(epizod_id):
    initialize_database()
    with closing(create_connection()) as connection:
        row = connection.execute(
            f"""
            SELECT {_episode_columns()}
            FROM pk_epizody e
            LEFT JOIN pk_programy p ON p.program_id = e.program_id
            LEFT JOIN pk_sciezki s ON s.sciezka_id = e.sciezka_id
            WHERE e.epizod_id = ?
            """,
            (epizod_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def list_episode_tasks(epizod_id) -> list[dict]:
    initialize_database()
    with closing(create_connection()) as connection:
        rows = connection.execute(
            """
            SELECT
                z.zadanie_id,
                z.epizod_id,
                z.element_id,
                e.lp,
                e.nazwa_w_sciezce,
                k.kod AS klocek_kod,
                k.nazwa AS klocek_nazwa,
                k.kolor AS klocek_kolor,
                k.kolor_tekstu AS klocek_kolor_tekstu,
                z.status,
                z.data_wymagana_do,
                z.data_zaplanowana,
                z.data_realizacji,
                z.zrodlo,
                z.uwagi,
                z.eskulap_system,
                z.eskulap_id
            FROM pk_zadania z
            LEFT JOIN pk_sciezka_elementy e
                ON e.element_id = z.element_id
            LEFT JOIN pk_klocki k ON k.klocek_id = e.klocek_id
            WHERE z.epizod_id = ?
            ORDER BY e.lp, z.zadanie_id
            """,
            (epizod_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_episode_process_elements(epizod_id) -> list[dict]:
    initialize_database()
    with closing(create_connection()) as connection:
        rows = connection.execute(
            """
            SELECT
                e.element_id,
                e.lp,
                e.nazwa_w_sciezce,
                k.kod AS klocek_kod,
                k.nazwa AS klocek_nazwa,
                k.kolor AS klocek_kolor,
                k.kolor_tekstu AS klocek_kolor_tekstu,
                z.zadanie_id,
                z.status,
                z.data_wymagana_do,
                z.data_zaplanowana,
                z.data_realizacji,
                z.zrodlo,
                z.eskulap_system,
                z.eskulap_id,
                z.uwagi
            FROM pk_epizody ep
            JOIN pk_sciezka_elementy e
                ON e.sciezka_id = ep.sciezka_id
               AND e.czy_aktywny = 1
            JOIN pk_klocki k ON k.klocek_id = e.klocek_id
            LEFT JOIN pk_zadania z
                ON z.epizod_id = ep.epizod_id
               AND z.element_id = e.element_id
            WHERE ep.epizod_id = ?
            ORDER BY e.lp, z.zadanie_id
            """,
            (epizod_id,),
        ).fetchall()
    return [dict(row) for row in rows]
