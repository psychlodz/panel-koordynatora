import sqlite3
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.repositories import pathway_repository


def main():
    with tempfile.TemporaryDirectory(prefix="kompas_tiles_") as temp_dir:
        database_path = Path(temp_dir) / "test.db"

        def create_test_connection():
            connection = sqlite3.connect(database_path)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            return connection

        connection = create_test_connection()
        connection.executescript(
            (PROJECT_ROOT / "db" / "schema.sql").read_text(encoding="utf-8")
        )
        with connection:
            program_id = connection.execute(
                """
                INSERT INTO pk_programy(kod, nazwa)
                VALUES ('TEST_KAFELKI', 'Test kafelków')
                """
            ).lastrowid
            sciezka_id = connection.execute(
                """
                INSERT INTO pk_sciezki(program_id, kod, nazwa)
                VALUES (?, 'TEST', 'Ścieżka testowa')
                """,
                (program_id,),
            ).lastrowid
            typ_id = connection.execute(
                """
                INSERT INTO pk_typy_elementow(kod, nazwa)
                VALUES ('TEST', 'Typ testowy')
                """
            ).lastrowid
            grupa_id = connection.execute(
                """
                INSERT INTO pk_grupy_klockow(kod, nazwa)
                VALUES ('TEST', 'Grupa testowa')
                """
            ).lastrowid
            klocek_id = connection.execute(
                """
                INSERT INTO pk_klocki(
                    kod, nazwa, typ_elementu_id, grupa_id
                )
                VALUES ('TEST', 'Klocek testowy', ?, ?)
                """,
                (typ_id, grupa_id),
            ).lastrowid
            element_ids = []
            for position, name in enumerate(("Pierwszy", "Drugi", "Trzeci"), 1):
                element_ids.append(
                    connection.execute(
                        """
                        INSERT INTO pk_sciezka_elementy(
                            sciezka_id,
                            klocek_id,
                            lp,
                            nazwa_w_sciezce
                        )
                        VALUES (?, ?, ?, ?)
                        """,
                        (sciezka_id, klocek_id, position, name),
                    ).lastrowid
                )
        connection.close()

        pathway_repository.initialize_local_db = lambda: database_path
        pathway_repository.create_local_connection = create_test_connection

        reordered = [element_ids[2], element_ids[0], element_ids[1]]
        pathway_repository.reorder_elements(sciezka_id, reordered)
        rows = pathway_repository.list_pathway_elements(sciezka_id)
        assert [row["element_id"] for row in rows] == reordered
        assert [row["lp"] for row in rows] == [1, 2, 3]
        print("Zmiana kolejności i przeliczenie lp: OK")

        connection = create_test_connection()
        with connection:
            epizod_id = connection.execute(
                """
                INSERT INTO pk_epizody(
                    pacjent_id,
                    program_id,
                    sciezka_id
                )
                VALUES ('PACJENT_TEST', ?, ?)
                """,
                (program_id, sciezka_id),
            ).lastrowid
            connection.execute(
                """
                INSERT INTO pk_zadania(epizod_id, element_id, status)
                VALUES (?, ?, 'ZREALIZOWANO')
                """,
                (epizod_id, element_ids[0]),
            )
            pending_task_id = connection.execute(
                """
                INSERT INTO pk_zadania(epizod_id, element_id, status)
                VALUES (?, ?, 'DO_ZAPLANOWANIA')
                """,
                (epizod_id, element_ids[1]),
            ).lastrowid
            connection.execute(
                """
                INSERT INTO pk_sciezka_zaleznosci(
                    sciezka_id,
                    element_od_id,
                    element_do_id,
                    typ
                )
                VALUES (?, ?, ?, 'KOLEJNOSC')
                """,
                (sciezka_id, element_ids[1], element_ids[2]),
            )
            connection.execute(
                """
                INSERT INTO pk_wyzwalacze(
                    element_id,
                    trigger_type,
                    trigger_element_id
                )
                VALUES (?, 'PO_ZAKONCZENIU', ?)
                """,
                (element_ids[1], element_ids[2]),
            )
        connection.close()

        assert not pathway_repository.can_delete_element(element_ids[0])
        assert not pathway_repository.can_insert_before(element_ids[0])
        print("Blokada elementu ze zrealizowanym zadaniem: OK")

        pathway_repository.delete_element_safe(element_ids[1])
        rows = pathway_repository.list_pathway_elements(sciezka_id)
        assert element_ids[1] not in {
            row["element_id"] for row in rows
        }
        assert [row["lp"] for row in rows] == [1, 2]

        connection = create_test_connection()
        dependency_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM pk_sciezka_zaleznosci
            WHERE element_od_id = ? OR element_do_id = ?
            """,
            (element_ids[1], element_ids[1]),
        ).fetchone()[0]
        trigger_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM pk_wyzwalacze
            WHERE element_id = ? OR trigger_element_id = ?
            """,
            (element_ids[1], element_ids[1]),
        ).fetchone()[0]
        pending_task_element = connection.execute(
            """
            SELECT element_id
            FROM pk_zadania
            WHERE zadanie_id = ?
            """,
            (pending_task_id,),
        ).fetchone()["element_id"]
        connection.close()
        assert dependency_count == 0
        assert trigger_count == 0
        assert pending_task_element is None
        print("Bezpieczne usunięcie i porządkowanie powiązań: OK")

        new_element_id = pathway_repository.add_element_at_position(
            sciezka_id,
            klocek_id,
            "Wstawiony przed pierwszym",
            before_element_id=element_ids[2],
        )
        rows = pathway_repository.list_pathway_elements(sciezka_id)
        assert [row["element_id"] for row in rows] == [
            new_element_id,
            element_ids[2],
            element_ids[0],
        ]
        assert [row["lp"] for row in rows] == [1, 2, 3]
        print("Dodanie elementu przed wskazaną pozycją: OK")

        try:
            pathway_repository.add_element_at_position(
                sciezka_id,
                klocek_id,
                "Niedozwolony element",
                before_element_id=element_ids[0],
            )
        except ValueError:
            pass
        else:
            raise AssertionError(
                "Dodanie przed zrealizowanym elementem nie zostało zablokowane"
            )
        print("Blokada wstawiania przed zrealizowanym elementem: OK")

    print("Wszystkie testy reguł kafelków zakończone powodzeniem.")


if __name__ == "__main__":
    main()
