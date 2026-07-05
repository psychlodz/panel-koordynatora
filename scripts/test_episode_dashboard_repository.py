import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.repositories import episode_dashboard_repository as repository


def main():
    with tempfile.TemporaryDirectory(
        prefix="kompas_dashboard_"
    ) as temp_dir:
        database_path = Path(temp_dir) / "dashboard.db"

        def create_connection():
            connection = sqlite3.connect(database_path)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            return connection

        connection = create_connection()
        connection.executescript(
            (PROJECT_ROOT / "db" / "schema.sql").read_text(
                encoding="utf-8"
            )
        )
        today = date.today()
        yesterday = today - timedelta(days=1)
        with connection:
            connection.execute(
                """
                INSERT INTO pk_users(
                    user_id,
                    login,
                    full_name,
                    password_hash
                )
                VALUES (101, 'koordynator_test', 'Koordynator Test', 'x')
                """
            )
            connection.execute(
                """
                INSERT INTO pk_user_units(
                    user_id,
                    jo_id,
                    jo_symbol,
                    jo_nazwa,
                    is_default
                )
                VALUES (101, 'JO1', 'JO1', 'Jednostka testowa', 1)
                """
            )
            program_id = connection.execute(
                """
                INSERT INTO pk_programy(kod, nazwa)
                VALUES ('DASH', 'Program dashboardu')
                """
            ).lastrowid
            pathway_id = connection.execute(
                """
                INSERT INTO pk_sciezki(program_id, kod, nazwa)
                VALUES (?, 'DASH', 'Ścieżka dashboardu')
                """,
                (program_id,),
            ).lastrowid
            connection.execute(
                """
                INSERT INTO pk_pathway_units(
                    sciezka_id,
                    jo_id,
                    jo_symbol,
                    jo_nazwa
                )
                VALUES (?, 'JO1', 'JO1', 'Jednostka testowa')
                """,
                (pathway_id,),
            )
            type_id = connection.execute(
                """
                INSERT INTO pk_typy_elementow(kod, nazwa)
                VALUES ('TEST', 'Typ testowy')
                """
            ).lastrowid
            group_id = connection.execute(
                """
                INSERT INTO pk_grupy_klockow(kod, nazwa)
                VALUES ('TEST', 'Grupa testowa')
                """
            ).lastrowid
            block_id = connection.execute(
                """
                INSERT INTO pk_klocki(
                    kod, nazwa, typ_elementu_id, grupa_id
                )
                VALUES ('DASH', 'Zadanie dashboardu', ?, ?)
                """,
                (type_id, group_id),
            ).lastrowid
            element_ids = []
            for lp, requires_order in ((1, 0), (2, 1), (3, 0)):
                element_ids.append(
                    connection.execute(
                        """
                        INSERT INTO pk_sciezka_elementy(
                            sciezka_id,
                            klocek_id,
                            lp,
                            nazwa_w_sciezce,
                            czy_wymaga_zlecenia
                        )
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            pathway_id,
                            block_id,
                            lp,
                            f"Zadanie {lp}",
                            requires_order,
                        ),
                    ).lastrowid
                )

            active_episode = connection.execute(
                """
                INSERT INTO pk_epizody(
                    pacjent_id,
                    program_id,
                    sciezka_id,
                    data_start,
                    status,
                    koordynator_id
                )
                VALUES ('PAC-1', ?, ?, ?, 'AKTYWNY', 'koordynator_test')
                """,
                (program_id, pathway_id, today.isoformat()),
            ).lastrowid
            completed_episode = connection.execute(
                """
                INSERT INTO pk_epizody(
                    pacjent_id,
                    program_id,
                    sciezka_id,
                    data_start,
                    data_zakonczenia,
                    status
                )
                VALUES ('PAC-2', ?, ?, ?, ?, 'ZAKONCZONY')
                """,
                (
                    program_id,
                    pathway_id,
                    today.isoformat(),
                    today.isoformat(),
                ),
            ).lastrowid
            connection.executemany(
                """
                INSERT INTO pk_zadania(
                    epizod_id,
                    element_id,
                    status,
                    data_wymagana_do,
                    data_zaplanowana
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        active_episode,
                        element_ids[0],
                        "ZREALIZOWANO",
                        None,
                        None,
                    ),
                    (
                        active_episode,
                        element_ids[1],
                        "DO_ZAPLANOWANIA",
                        yesterday.isoformat(),
                        None,
                    ),
                    (
                        active_episode,
                        element_ids[2],
                        "ZAPLANOWANO",
                        None,
                        today.isoformat(),
                    ),
                    (
                        completed_episode,
                        element_ids[0],
                        "ZREALIZOWANO",
                        None,
                        None,
                    ),
                ],
            )
        connection.close()

        repository.initialize_local_db = lambda: database_path
        repository.create_local_connection = create_connection
        repository.patient_id_column = (
            lambda alias=None: (
                f"{alias}.pacjent_id" if alias else "pacjent_id"
            )
        )

        summary = repository.get_dashboard_summary()
        assert summary == {
            "active_episodes": 1,
            "episodes_to_plan": 1,
            "overdue_episodes": 1,
            "tasks_scheduled_today": 1,
            "waiting_for_eskulap": 1,
            "completed_this_month": 1,
        }

        progress = repository.get_episode_progress(active_episode)
        assert progress["liczba_zadan"] == 3
        assert progress["liczba_zrealizowanych_zadan"] == 1
        assert progress["procent_realizacji"] == 33.3

        next_task = repository.get_next_task(active_episode)
        assert next_task["nazwa"] == "Zadanie 2"
        assert next_task["termin"] == yesterday.isoformat()

        overdue = repository.list_dashboard_episodes(
            status_filter=repository.FILTER_OVERDUE
        )
        assert [row["epizod_id"] for row in overdue] == [active_episode]

        user = SimpleNamespace(user_id=101, is_admin=False)
        scoped = repository.list_dashboard_episodes(current_user=user)
        assert len(scoped) == 2
        assert scoped[0]["unit_symbols"] == ["JO1"]

        print("Podsumowanie dashboardu: OK")
        print("Postęp i najbliższe zadanie: OK")
        print("Filtry statusu i jednostek: OK")


if __name__ == "__main__":
    main()
