from contextlib import closing

from local_db import create_local_connection, initialize_local_db


EPISODE_COLUMNS = """
    e.epizod_id,
    e.pacjent_id,
    e.program_id,
    e.sciezka_id,
    e.data_start,
    e.data_zakonczenia,
    e.status,
    e.koordynator_id,
    e.uwagi,
    e.created_at,
    e.updated_at,
    p.kod AS program_kod,
    p.nazwa AS program_nazwa,
    s.kod AS sciezka_kod,
    s.nazwa AS sciezka_nazwa
"""


def list_active_episodes() -> list[dict]:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        rows = connection.execute(
            f"""
            SELECT {EPISODE_COLUMNS}
            FROM pk_epizody e
            LEFT JOIN pk_programy p ON p.program_id = e.program_id
            LEFT JOIN pk_sciezki s ON s.sciezka_id = e.sciezka_id
            WHERE e.data_zakonczenia IS NULL
            ORDER BY e.data_start DESC, e.epizod_id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_episode(epizod_id):
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        row = connection.execute(
            f"""
            SELECT {EPISODE_COLUMNS}
            FROM pk_epizody e
            LEFT JOIN pk_programy p ON p.program_id = e.program_id
            LEFT JOIN pk_sciezki s ON s.sciezka_id = e.sciezka_id
            WHERE e.epizod_id = ?
            """,
            (epizod_id,),
        ).fetchone()
    return dict(row) if row is not None else None
