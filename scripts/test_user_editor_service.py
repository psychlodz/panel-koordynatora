import tempfile
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.repositories import user_unit_repository
from app.repositories.db_connection import (
    DatabaseSettings,
    create_connection,
    initialize_database,
)
from app.services import auth_service


def main():
    with tempfile.TemporaryDirectory(
        prefix="kompas_user_editor_"
    ) as temp:
        database_path = Path(temp) / "kompas_test.db"
        settings = DatabaseSettings(
            engine="sqlite",
            sqlite_path=str(database_path),
        )
        initialize_database(settings)

        auth_service.initialize_local_db = lambda: database_path
        auth_service.create_local_connection = (
            lambda: create_connection(settings)
        )
        user_unit_repository.initialize_local_db = lambda: database_path
        user_unit_repository.create_local_connection = (
            lambda: create_connection(settings)
        )

        admin = auth_service.login("admin", "admin")
        try:
            auth_service.create_user(
                admin.user_id,
                login="bez.jednostki",
                full_name="Użytkownik Bez Jednostki",
                password="Testowe123!",
                role_codes=["KOORDYNATOR"],
                units=[],
            )
        except ValueError:
            pass
        else:
            raise AssertionError(
                "Utworzenie użytkownika bez jednostki powinno być odrzucone"
            )
        assert all(
            user["login"] != "bez.jednostki"
            for user in auth_service.list_users(admin.user_id)
        )

        user_id = auth_service.create_user(
            admin.user_id,
            login="koordynator.test",
            full_name="Koordynator Testowy",
            password="Testowe123!",
            role_codes=["KOORDYNATOR"],
            units=[
                {
                    "jo_id": "101",
                    "jo_symbol": "JO101",
                    "jo_nazwa": "Jednostka pierwsza",
                },
                {
                    "jo_id": "202",
                    "jo_symbol": "JO202",
                    "jo_nazwa": "Jednostka druga",
                },
            ],
        )
        units = user_unit_repository.list_user_units(user_id)
        assert len(units) == 2
        assert units[0]["jo_id"] == "101"
        assert units[0]["is_default"] == 1

        auth_service.update_user(
            admin.user_id,
            user_id,
            login="koordynator.edytowany",
            full_name="Koordynator Edytowany",
            role_codes=["KIEROWNIK"],
            units=[
                {
                    "jo_id": "101",
                    "jo_symbol": "JO101",
                    "jo_nazwa": "Jednostka pierwsza",
                },
                {
                    "jo_id": "202",
                    "jo_symbol": "JO202",
                    "jo_nazwa": "Jednostka druga",
                },
            ],
            default_unit_id="202",
        )
        users = auth_service.list_users(admin.user_id)
        edited = next(
            user for user in users if user["user_id"] == user_id
        )
        assert edited["login"] == "koordynator.edytowany"
        assert edited["full_name"] == "Koordynator Edytowany"
        assert edited["roles"] == "KIEROWNIK"
        units = user_unit_repository.list_user_units(user_id)
        assert len(units) == 2
        assert units[0]["jo_id"] == "202"
        assert units[0]["is_default"] == 1

    print("Dodawanie i edycja użytkownika z rolami i jednostkami: OK")


if __name__ == "__main__":
    main()
