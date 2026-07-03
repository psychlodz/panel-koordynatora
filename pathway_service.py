from contextlib import closing

from episode_generator import (
    activate_next_tasks,
    complete_task,
    create_episode_with_tasks,
)
from local_db import create_local_connection, initialize_local_db


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
