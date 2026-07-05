import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.repositories import (
    dependency_repository,
    episode_repository,
    pathway_repository,
    pathway_unit_repository,
    program_repository,
    program_unit_repository,
    role_repository,
    task_repository,
    trigger_repository,
    user_unit_repository,
    user_repository,
)
from app.repositories.db_connection import (
    DatabaseSettings,
    create_connection,
    initialize_database,
)
from app.services import auth_service


def main():
    with tempfile.TemporaryDirectory(prefix="kompas_db_sqlite_") as temp:
        database_path = Path(temp) / "kompas_test.db"
        settings = DatabaseSettings(
            engine="sqlite",
            sqlite_path=str(database_path),
        )
        initialize_database(settings)

        program_repository.initialize_local_db = lambda: database_path
        program_repository.create_local_connection = (
            lambda: create_connection(settings)
        )
        legacy_repositories = (
            pathway_repository,
            episode_repository,
            task_repository,
            dependency_repository,
            trigger_repository,
            user_unit_repository,
            program_unit_repository,
            pathway_unit_repository,
        )
        for repository in legacy_repositories:
            repository.initialize_local_db = lambda: database_path
            repository.create_local_connection = (
                lambda: create_connection(settings)
            )
        user_repository.initialize_database = lambda: database_path
        user_repository.create_connection = lambda: create_connection(
            settings
        )
        role_repository.initialize_database = lambda: database_path
        role_repository.create_connection = lambda: create_connection(
            settings
        )
        auth_service.initialize_local_db = lambda: database_path
        auth_service.create_local_connection = lambda: create_connection(
            settings
        )

        program_id = program_repository.create_program(
            "DBPG2_SQLITE",
            "Test wspólnej warstwy SQLite",
        )
        program = program_repository.get_program(program_id)
        assert program["kod"] == "DBPG2_SQLITE"

        program_repository.update_program(
            program_id,
            "DBPG2_SQLITE",
            "Zaktualizowany test SQLite",
            czy_aktywny=1,
        )
        updated = program_repository.get_program(program_id)
        assert updated["nazwa"] == "Zaktualizowany test SQLite"
        assert any(
            row["program_id"] == program_id
            for row in program_repository.list_programs()
        )
        admin = user_repository.get_user_by_login("ADMIN")
        assert admin["login"] == "admin"
        authenticated = auth_service.login("ADMIN", "admin")
        assert authenticated.user_id == admin["user_id"]
        assert authenticated.is_admin
        assert {
            role["code"]
            for role in role_repository.list_roles()
        } >= {"ADMIN", "KOORDYNATOR", "KIEROWNIK"}

        pathways = pathway_repository.list_pathways(
            next(
                row["program_id"]
                for row in program_repository.list_programs()
                if row["kod"] == "ADHD_DZ_ML"
            )
        )
        assert pathways
        pathway_id = pathways[0]["sciezka_id"]
        elements = pathway_repository.list_pathway_elements(pathway_id)
        assert elements
        assert isinstance(
            dependency_repository.list_dependencies(pathway_id),
            list,
        )
        assert isinstance(
            trigger_repository.list_triggers(elements[0]["element_id"]),
            list,
        )
        assert episode_repository.list_episodes() == []
        assert task_repository.list_active_tasks() == []
        assert user_unit_repository.list_user_units(admin["user_id"]) == []
        assert program_unit_repository.list_program_units(program_id) == []
        assert pathway_unit_repository.list_pathway_units(pathway_id) == []

    print("Wspólna warstwa SQLite: OK")


if __name__ == "__main__":
    main()
