import sys
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.repositories.db_connection import (
    create_connection,
    initialize_database,
)
from pathway_service import create_episode_with_tasks, list_episode_tasks


def main():
    initialize_database()

    with closing(create_connection()) as connection:
        pathway = connection.execute(
            """
            SELECT p.program_id, s.sciezka_id
            FROM pk_programy p
            JOIN pk_sciezki s ON s.program_id = p.program_id
            WHERE p.kod = 'ADHD_DZ_ML'
              AND s.kod = 'PODSTAWOWA'
            """
        ).fetchone()

    if pathway is None:
        raise RuntimeError(
            "Brak testowej ścieżki ADHD w bazie PostgreSQL"
        )

    pacjent_id = f"TEST-{datetime.now():%Y%m%d%H%M%S%f}"
    epizod_id = create_episode_with_tasks(
        pacjent_id=pacjent_id,
        program_id=pathway["program_id"],
        sciezka_id=pathway["sciezka_id"],
        data_start=date.today().isoformat(),
        koordynator_id="TEST",
        uwagi="Epizod utworzony przez skrypt manualny",
    )

    print(f"Utworzono epizod {epizod_id} dla pacjenta {pacjent_id}.")
    for task in list_episode_tasks(epizod_id):
        print(
            f"{task['lp']}. {task['nazwa_w_sciezce']} "
            f"[{task['klocek_kod']}] — {task['status']}"
        )


if __name__ == "__main__":
    main()
