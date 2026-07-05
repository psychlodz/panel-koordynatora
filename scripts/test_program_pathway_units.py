import sqlite3
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.repositories import (
    pathway_unit_repository,
    program_repository,
    program_unit_repository,
)


def main():
    with tempfile.TemporaryDirectory(
        prefix="kompas_program_units_"
    ) as temp_dir:
        database_path = Path(temp_dir) / "test.db"

        def create_connection():
            connection = sqlite3.connect(database_path)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            return connection

        connection = create_connection()
        connection.executescript(
            (PROJECT_ROOT / "db" / "schema.sql").read_text(encoding="utf-8")
        )
        with connection:
            program_id = connection.execute(
                """
                INSERT INTO pk_programy(kod, nazwa)
                VALUES ('TEST_JO', 'Program testowy')
                """
            ).lastrowid
            sciezka_id = connection.execute(
                """
                INSERT INTO pk_sciezki(program_id, kod, nazwa)
                VALUES (?, 'TEST_JO', 'Ścieżka testowa')
                """,
                (program_id,),
            ).lastrowid
        connection.close()

        for repository in (
            program_repository,
            program_unit_repository,
            pathway_unit_repository,
        ):
            repository.initialize_local_db = lambda: database_path
            repository.create_local_connection = create_connection

        program_unit_repository.assign_unit_to_program(
            program_id, 303, "JO303", "Jednostka programu"
        )
        pathway_unit_repository.assign_unit_to_pathway(
            sciezka_id, 404, "JO404", "Jednostka ścieżki"
        )
        assert len(
            program_unit_repository.list_program_units(program_id)
        ) == 1
        assert len(
            pathway_unit_repository.list_pathway_units(sciezka_id)
        ) == 1
        print("Przypisanie jednostek do programu i ścieżki: OK")

        program_unit_repository.remove_unit_from_program(program_id, 303)
        pathway_unit_repository.remove_unit_from_pathway(sciezka_id, 404)
        assert not program_unit_repository.list_program_units(program_id)
        assert not pathway_unit_repository.list_pathway_units(sciezka_id)
        print("Usunięcie przypisań: OK")

        edited_program_id = program_repository.create_program(
            "TEST_FORM",
            "Program formularza",
            units=[
                {
                    "jo_id": "501",
                    "jo_symbol": "JO501",
                    "jo_nazwa": "Jednostka pierwsza",
                },
                {
                    "jo_id": "502",
                    "jo_symbol": "JO502",
                    "jo_nazwa": "Jednostka druga",
                },
            ],
        )
        programs = {
            row["program_id"]: row
            for row in program_repository.list_programs()
        }
        assert programs[edited_program_id]["jednostki"] == "JO501, JO502"

        program_repository.update_program(
            edited_program_id,
            "TEST_FORM",
            "Program formularza",
            units=[
                {
                    "jo_id": "502",
                    "jo_symbol": "JO502",
                    "jo_nazwa": "Jednostka druga",
                }
            ],
        )
        assigned = program_unit_repository.list_program_units(
            edited_program_id
        )
        assert [row["jo_id"] for row in assigned] == ["502"]
        print("Zapis jednostek z formularza programu: OK")

    print("Test jednostek programu i ścieżki zakończony powodzeniem.")


if __name__ == "__main__":
    main()
