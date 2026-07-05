import io
import logging
import sqlite3
import sys
import tempfile
import types
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import oracledb  # noqa: F401
except ModuleNotFoundError:
    sys.modules["oracledb"] = types.SimpleNamespace()

import episode_generator
from app.repositories import (
    episode_dashboard_repository,
    episode_repository,
    qualification_repository,
)


VISIT_ID = "TEST-F18-001"
PATIENT_ID = "PACJENT-TEST-001"


def _connection(database_path):
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _prepare_database(database_path):
    connection = _connection(database_path)
    try:
        for script_name in ("schema.sql", "seed.sql", "migrations.sql"):
            connection.executescript(
                (PROJECT_ROOT / "db" / script_name).read_text(
                    encoding="utf-8"
                )
            )
    finally:
        connection.close()


def _oracle_visit():
    return {
        "wizyta_id": VISIT_ID,
        "pacjent_id": PATIENT_ID,
        "data_wizyty": "2026-07-05",
        "parametr_kod": "F18",
        "poradnia_id": "PKK-TEST",
        "poradnia_symbol": "PKK",
        "poradnia_nazwa": "Punkt testowy",
        "pracownik": "Testowy Pracownik",
    }


def _configure_repositories(database_path):
    factory = lambda: _connection(database_path)

    episode_generator.initialize_local_db = lambda: database_path
    episode_generator.create_local_connection = factory
    episode_generator.patient_id_column = lambda alias=None: (
        f"{alias}.pacjent_id" if alias else "pacjent_id"
    )

    qualification_repository.initialize_local_db = lambda: database_path
    qualification_repository.create_local_connection = factory
    qualification_repository._oracle_query = (
        lambda _sql, parameters=None, fetch_one=False: (
            dict(_oracle_visit())
            if fetch_one
            else [dict(_oracle_visit())]
        )
    )

    episode_repository.initialize_local_db = lambda: database_path
    episode_repository.create_local_connection = factory
    episode_repository.patient_id_column = lambda alias=None: (
        f"{alias}.pacjent_id" if alias else "pacjent_id"
    )

    episode_dashboard_repository.initialize_local_db = (
        lambda: database_path
    )
    episode_dashboard_repository.create_local_connection = factory
    episode_dashboard_repository.patient_id_column = (
        lambda alias=None: (
            f"{alias}.pacjent_id" if alias else "pacjent_id"
        )
    )


def _adhd_ids(database_path):
    connection = _connection(database_path)
    try:
        row = connection.execute(
            """
            SELECT p.program_id, s.sciezka_id
            FROM pk_programy p
            JOIN pk_sciezki s ON s.program_id = p.program_id
            WHERE p.kod = 'ADHD_DZ_ML'
              AND s.kod = 'PODSTAWOWA'
            """
        ).fetchone()
        return int(row["program_id"]), int(row["sciezka_id"])
    finally:
        connection.close()


def _capture_debug_logs():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.DEBUG)
    for logger in (
        logging.getLogger("episode_generator"),
        logging.getLogger(
            "app.repositories.qualification_repository"
        ),
    ):
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
    return stream, handler


def main():
    with tempfile.TemporaryDirectory(
        prefix="kompas_qualification_flow_"
    ) as temp_dir:
        database_path = Path(temp_dir) / "qualification.db"
        _prepare_database(database_path)
        _configure_repositories(database_path)
        program_id, pathway_id = _adhd_ids(database_path)
        log_stream, handler = _capture_debug_logs()

        try:
            episode_id = (
                qualification_repository
                .create_episode_from_qualification_visit(
                    VISIT_ID,
                    program_id,
                    pathway_id,
                    koordynator_id="koordynator-test",
                )
            )

            activate_tasks = episode_generator._activate_triggered_tasks
            episode_generator._activate_triggered_tasks = (
                lambda *_args, **_kwargs: (
                    (_ for _ in ()).throw(
                        RuntimeError("Kontrolowany błąd testowy")
                    )
                )
            )
            try:
                episode_generator.create_episode_with_tasks(
                    "PACJENT-ROLLBACK",
                    program_id,
                    pathway_id,
                    "2026-07-05",
                    source_system="TEST",
                    source_type="ROLLBACK",
                    source_id="ROLLBACK-001",
                )
            except RuntimeError:
                pass
            else:
                raise AssertionError("Oczekiwano kontrolowanego błędu")
            finally:
                episode_generator._activate_triggered_tasks = (
                    activate_tasks
                )
        finally:
            for logger in (
                logging.getLogger("episode_generator"),
                logging.getLogger(
                    "app.repositories.qualification_repository"
                ),
            ):
                logger.removeHandler(handler)

        connection = _connection(database_path)
        try:
            episode = connection.execute(
                """
                SELECT *
                FROM pk_epizody
                WHERE epizod_id = ?
                """,
                (episode_id,),
            ).fetchone()
            tasks = connection.execute(
                """
                SELECT *
                FROM pk_zadania
                WHERE epizod_id = ?
                """,
                (episode_id,),
            ).fetchall()
            rolled_back = connection.execute(
                """
                SELECT COUNT(*)
                FROM pk_epizody
                WHERE source_system = 'TEST'
                  AND source_type = 'ROLLBACK'
                  AND source_id = 'ROLLBACK-001'
                """
            ).fetchone()[0]
        finally:
            connection.close()

        assert episode is not None
        assert episode["pacjent_id"] == PATIENT_ID
        assert episode["source_id"] == VISIT_ID
        assert len(tasks) >= 1
        assert rolled_back == 0
        print(f"EPIZOD_CREATED: OK ({episode_id})")
        print(f"TASKS_CREATED: OK ({len(tasks)})")
        print("ROLLBACK: OK")

        remaining = qualification_repository.list_qualification_visits(
            only_unassigned=True
        )
        assert remaining == []
        print("Filtr nieprzypisanych wizyt: OK")

        active_ids = {
            row["epizod_id"]
            for row in episode_repository.list_active_episodes()
        }
        assert episode_id in active_ids
        print("Widoczność w module Epizody: OK")

        dashboard_ids = {
            row["epizod_id"]
            for row in (
                episode_dashboard_repository
                .list_dashboard_episodes()
            )
        }
        assert episode_id in dashboard_ids
        print("Widoczność w Dashboardzie: OK")

        logs = log_stream.getvalue()
        for marker in (
            "START_KWALIFIKACJI",
            "EPIZOD_CREATED",
            "TASKS_CREATED",
            "COMMIT_OK",
            "ROLLBACK",
        ):
            assert marker in logs
        print("Logowanie DEBUG: OK")

    print("Pełny przepływ kwalifikacji zakończony powodzeniem.")


if __name__ == "__main__":
    main()
