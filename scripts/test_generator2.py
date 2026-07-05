import sys
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from episode_generator import complete_task, create_episode_with_tasks
from local_db import create_local_connection, initialize_local_db
from pathway_service import list_episode_tasks


def _adhd_pathway():
    with closing(create_local_connection()) as connection:
        return connection.execute(
            """
            SELECT p.program_id, s.sciezka_id
            FROM pk_programy p
            JOIN pk_sciezki s ON s.program_id = p.program_id
            WHERE p.kod = 'ADHD_DZ_ML'
              AND s.kod = 'PODSTAWOWA'
            """
        ).fetchone()


def _print_tasks(title, epizod_id):
    tasks = list_episode_tasks(epizod_id)
    print(title)
    for task in tasks:
        print(
            f"  {task['lp']}. {task['nazwa_w_sciezce']} "
            f"[{task['klocek_kod']}] - {task['status']}"
        )
    return tasks


def main():
    initialize_local_db()
    pathway = _adhd_pathway()
    if pathway is None:
        raise RuntimeError("Brak testowej ścieżki ADHD w lokalnej bazie")

    epizod_id = create_episode_with_tasks(
        pacjent_id=f"GEN2-{datetime.now():%Y%m%d%H%M%S%f}",
        program_id=pathway["program_id"],
        sciezka_id=pathway["sciezka_id"],
        data_start=date.today().isoformat(),
        koordynator_id="TEST",
        uwagi="Test generatora epizodów 2.0",
    )

    tasks = _print_tasks("Zadania po utworzeniu epizodu:", epizod_id)
    initial_codes = {task["klocek_kod"] for task in tasks}
    expected_initial = {"PKK_KWAL", "WIZYTA_PSYCHIATRYCZNA"}
    if initial_codes != expected_initial:
        raise AssertionError(
            f"Oczekiwano {expected_initial}, otrzymano {initial_codes}"
        )

    psychiatry_task = next(
        task
        for task in tasks
        if task["klocek_kod"] == "WIZYTA_PSYCHIATRYCZNA"
    )
    complete_task(psychiatry_task["zadanie_id"])

    tasks = _print_tasks(
        "Zadania po zakończeniu wizyty psychiatrycznej:",
        epizod_id,
    )
    final_codes = {task["klocek_kod"] for task in tasks}
    if "DIAGNOSTYKA_PSYCHOLOGICZNA" not in final_codes:
        raise AssertionError("Nie utworzono zadania dla psychologa")

    print("Test generatora 2.0 zakończony powodzeniem.")


if __name__ == "__main__":
    main()
