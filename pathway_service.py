from contextlib import closing

from local_db import create_local_connection, initialize_local_db


def create_episode_with_tasks(
    pacjent_id,
    program_id,
    sciezka_id,
    data_start,
    koordynator_id=None,
    uwagi=None,
) -> int:
    if not str(pacjent_id).strip():
        raise ValueError("pacjent_id jest wymagany")

    initialize_local_db()

    with closing(create_local_connection()) as connection:
        with connection:
            pathway = connection.execute(
                """
                SELECT sciezka_id
                FROM pk_sciezki
                WHERE sciezka_id = ?
                  AND program_id = ?
                  AND czy_aktywna = 1
                """,
                (sciezka_id, program_id),
            ).fetchone()
            if pathway is None:
                raise ValueError(
                    "Nie znaleziono aktywnej ścieżki dla wybranego programu"
                )

            cursor = connection.execute(
                """
                INSERT INTO pk_epizody(
                    pacjent_id,
                    program_id,
                    sciezka_id,
                    data_start,
                    status,
                    koordynator_id,
                    uwagi
                )
                VALUES (?, ?, ?, ?, 'NOWY', ?, ?)
                """,
                (
                    pacjent_id,
                    program_id,
                    sciezka_id,
                    data_start,
                    koordynator_id,
                    uwagi,
                ),
            )
            epizod_id = cursor.lastrowid

            elements = connection.execute(
                """
                SELECT element_id
                FROM pk_sciezka_elementy
                WHERE sciezka_id = ?
                  AND czy_aktywny = 1
                  AND czy_obowiazkowy = 1
                  AND czy_wymaga_zlecenia = 0
                ORDER BY lp
                """,
                (sciezka_id,),
            ).fetchall()

            connection.executemany(
                """
                INSERT INTO pk_zadania(
                    epizod_id,
                    element_id,
                    status,
                    zrodlo
                )
                VALUES (?, ?, 'DO_ZAPLANOWANIA', 'PROGRAM')
                """,
                [(epizod_id, row["element_id"]) for row in elements],
            )

    return int(epizod_id)


def list_episode_tasks(epizod_id) -> list[dict]:
    initialize_local_db()

    with closing(create_local_connection()) as connection:
        rows = connection.execute(
            """
            SELECT
                z.zadanie_id,
                z.epizod_id,
                z.element_id,
                z.status,
                z.data_wymagana_do,
                z.data_zaplanowana,
                z.data_realizacji,
                z.zrodlo,
                z.eskulap_system,
                z.eskulap_id,
                z.uwagi,
                e.lp,
                e.nazwa_w_sciezce,
                k.kod AS klocek_kod,
                k.nazwa AS klocek_nazwa
            FROM pk_zadania z
            LEFT JOIN pk_sciezka_elementy e
                ON e.element_id = z.element_id
            LEFT JOIN pk_klocki k
                ON k.klocek_id = e.klocek_id
            WHERE z.epizod_id = ?
            ORDER BY e.lp, z.zadanie_id
            """,
            (epizod_id,),
        ).fetchall()

    return [dict(row) for row in rows]
