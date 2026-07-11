import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from episode_generator import complete_task, create_episode_with_tasks
from app.repositories.db_connection import create_connection, initialize_database
from app.repositories.episode_element_repository import (
    can_deactivate_element,
    list_element_history,
    list_episode_elements,
)
from app.services.episode_path_service import (
    deactivate_element,
    duplicate_element,
    reactivate_element,
)


@dataclass(frozen=True)
class TestUser:
    user_id: int = 1
    roles: frozenset[str] = frozenset({"ADMIN"})

    @property
    def is_admin(self):
        return True


def _fetchone(connection, sql, params=()):
    row = connection.execute(sql, params).fetchone()
    if row is None:
        raise AssertionError("Brak wymaganych danych testowych")
    return row


def _cleanup(connection, source_id):
    episodes = connection.execute(
        """
        SELECT epizod_id
        FROM pk_epizody
        WHERE source_system = 'TEST'
          AND source_type = 'EPISODE_PATH_EDITING'
          AND source_id = ?
        """,
        (source_id,),
    ).fetchall()
    for episode in episodes:
        epizod_id = episode["epizod_id"]
        connection.execute(
            "DELETE FROM pk_zadania WHERE epizod_id = ?",
            (epizod_id,),
        )
        connection.execute(
            "DELETE FROM pk_epizod_elementy_historia WHERE epizod_id = ?",
            (epizod_id,),
        )
        connection.execute(
            "DELETE FROM pk_epizod_elementy WHERE epizod_id = ?",
            (epizod_id,),
        )
        connection.execute(
            "DELETE FROM pk_epizody WHERE epizod_id = ?",
            (epizod_id,),
        )


def main():
    initialize_database()
    source_id = "TEST_EPISODE_PATH_EDITING"
    user = TestUser()

    with create_connection() as connection:
        _cleanup(connection, source_id)
        program = _fetchone(
            connection,
            "SELECT program_id FROM pk_programy WHERE kod = 'ADHD_DZ_ML'",
        )
        pathway = _fetchone(
            connection,
            """
            SELECT sciezka_id
            FROM pk_sciezki
            WHERE program_id = ?
              AND kod = 'PODSTAWOWA'
            """,
            (program["program_id"],),
        )
        template_count_before = _fetchone(
            connection,
            """
            SELECT COUNT(*) AS count
            FROM pk_sciezka_elementy
            WHERE sciezka_id = ?
            """,
            (pathway["sciezka_id"],),
        )["count"]
        connection.commit()

    epizod_id = create_episode_with_tasks(
        pacjent_id="TEST_EPISODE_PATH_PATIENT",
        program_id=program["program_id"],
        sciezka_id=pathway["sciezka_id"],
        data_start="2026-01-01",
        koordynator_id=str(user.user_id),
        source_system="TEST",
        source_type="EPISODE_PATH_EDITING",
        source_id=source_id,
    )

    elements = list_episode_elements(epizod_id)
    if not elements:
        raise AssertionError("Nie utworzono instancji elementów epizodu")
    print(f"Utworzono elementów epizodu: {len(elements)}")

    inactive_candidate = next(
        element
        for element in elements
        if not element.get("zadanie_id")
    )
    deactivate_element(
        inactive_candidate["epizod_element_id"],
        "Test dezaktywacji elementu niezrealizowanego",
        user,
    )
    deactivated = next(
        element
        for element in list_episode_elements(epizod_id)
        if element["epizod_element_id"]
        == inactive_candidate["epizod_element_id"]
    )
    assert int(deactivated["czy_aktywny"]) == 0
    print("Dezaktywacja elementu niezrealizowanego: OK")

    reactivate_element(
        inactive_candidate["epizod_element_id"],
        "Test reaktywacji elementu",
        user,
        create_task=True,
    )
    reactivated = next(
        element
        for element in list_episode_elements(epizod_id)
        if element["epizod_element_id"]
        == inactive_candidate["epizod_element_id"]
    )
    assert int(reactivated["czy_aktywny"]) == 1
    print("Reaktywacja elementu: OK")

    task_element = next(
        element
        for element in list_episode_elements(epizod_id)
        if element.get("zadanie_id")
    )
    complete_task(task_element["zadanie_id"])
    block = can_deactivate_element(task_element["epizod_element_id"])
    assert not block["allowed"]
    print("Blokada dezaktywacji elementu zrealizowanego: OK")

    duplicated = duplicate_element(
        task_element["epizod_element_id"],
        {
            "nazwa": f"{task_element['nazwa']} — powielenie testowe",
            "lp": int(task_element["lp"]) + 10,
            "min_liczba": 1,
            "max_liczba": 1,
        },
        "Test powielenia elementu zrealizowanego",
        user,
    )
    duplicated_elements = list_episode_elements(epizod_id)
    duplicate_row = next(
        element
        for element in duplicated_elements
        if element["epizod_element_id"] == duplicated["epizod_element_id"]
    )
    assert duplicate_row["typ_pochodzenia"] == "POWIELENIE"
    assert duplicate_row["zadanie_id"] == duplicated["zadanie_id"]
    assert str(duplicate_row["status"]).upper() != "ZAKONCZONE"
    print("Powielenie elementu i nowe zadanie: OK")

    history = list_element_history(duplicated["epizod_element_id"])
    assert any(row["operacja"] == "POWIELENIE" for row in history)
    print("Historia zmian: OK")

    try:
        duplicate_element(
            task_element["epizod_element_id"],
            {
                "nazwa": "Błędne wstawienie przed częścią zrealizowaną",
                "lp": 1,
                "min_liczba": 1,
                "max_liczba": 1,
            },
            "Test blokady kolejności",
            user,
        )
    except ValueError:
        print("Blokada dodania przed elementem zrealizowanym: OK")
    else:
        raise AssertionError(
            "Powinno być zablokowane dodanie przed zrealizowaną częścią"
        )

    with create_connection() as connection:
        template_count_after = _fetchone(
            connection,
            """
            SELECT COUNT(*) AS count
            FROM pk_sciezka_elementy
            WHERE sciezka_id = ?
            """,
            (pathway["sciezka_id"],),
        )["count"]
        assert template_count_after == template_count_before
        other_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM pk_epizod_elementy
            WHERE epizod_id <> ?
              AND element_zrodlowy_id = ?
            """,
            (epizod_id, task_element["epizod_element_id"]),
        ).fetchone()["count"]
        assert other_count == 0
        _cleanup(connection, source_id)
        connection.commit()
    print("Brak zmian we wzorcowej ścieżce i innych epizodach: OK")


if __name__ == "__main__":
    main()
