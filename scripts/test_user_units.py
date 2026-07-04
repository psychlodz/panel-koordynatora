import sqlite3
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.repositories import user_unit_repository


def main():
    with tempfile.TemporaryDirectory(prefix="kompas_user_units_") as temp_dir:
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
            user_id = connection.execute(
                """
                INSERT INTO pk_users(login, full_name, password_hash)
                VALUES ('test_units', 'Test Jednostek', 'test_hash')
                """
            ).lastrowid
        connection.close()

        user_unit_repository.initialize_local_db = lambda: database_path
        user_unit_repository.create_local_connection = create_connection

        user_unit_repository.assign_unit_to_user(
            user_id, 101, "JO101", "Jednostka pierwsza"
        )
        user_unit_repository.assign_unit_to_user(
            user_id, 202, "JO202", "Jednostka druga"
        )
        units = user_unit_repository.list_user_units(user_id)
        assert len(units) == 2
        assert units[0]["jo_id"] == "101"
        assert units[0]["is_default"] == 1
        print("Pierwsza jednostka została domyślną: OK")

        user_unit_repository.set_default_unit(user_id, 202)
        default = user_unit_repository.get_default_unit(user_id)
        assert default["jo_id"] == "202"
        print("Zmiana jednostki domyślnej: OK")

        user_unit_repository.remove_unit_from_user(user_id, 202)
        units = user_unit_repository.list_user_units(user_id)
        assert len(units) == 1
        assert units[0]["jo_id"] == "101"
        assert units[0]["is_default"] == 1
        print("Automatyczny wybór domyślnej po usunięciu: OK")

    print("Test jednostek użytkownika zakończony powodzeniem.")


if __name__ == "__main__":
    main()
