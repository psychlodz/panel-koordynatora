from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.modules.setdefault("oracledb", SimpleNamespace(connect=lambda *a, **k: None))

from app.services.episode_synchronization_service import (
    PKK_KWAL_BLOCK_CODE,
    EpisodeSynchronizationService,
    match_consultations_to_elements,
    match_visits_to_elements,
)
from app.repositories.episode_element_repository import record_history
from app.repositories import event_repository
from app.services.episode_state_service import (
    EpisodeStateService,
    STATUS_PLANNED,
)


def visit(oracle_id, code, when, decision="J", name=None):
    return SimpleNamespace(
        oracle_id=str(oracle_id),
        source="ESKULAP",
        parametr_kod=code,
        parametr_nazwa=name or code,
        event_date=datetime.fromisoformat(when),
        status=decision,
        employee_name="Lekarz Testowy",
    )


def consultation(oracle_id, planned_when):
    return SimpleNamespace(
        oracle_id=str(oracle_id),
        source="ESK_RAPORTY.V_KOMPAS_KONSULTACJE",
        event_type="CONSULTATION",
        event_date=None,
        planned_date=datetime.fromisoformat(planned_when),
        status=None,
        description="Konsultacja specjalistyczna",
    )


def element(element_id, block_code, lp, eskulap_id=None):
    return {
        "epizod_element_id": element_id,
        "klocek_kod": block_code,
        "lp": lp,
        "eskulap_id": eskulap_id,
    }


class FakeConnection:
    def __init__(self):
        self.insert_parameters = None

    def execute(self, sql, parameters=()):
        normalized = " ".join(sql.split()).upper()
        if normalized.startswith("SELECT * FROM PK_EPIZOD_ELEMENTY"):
            return SimpleNamespace(
                fetchone=lambda: {
                    "epizod_element_id": parameters[0],
                    "epizod_id": 77,
                }
            )
        if normalized.startswith("INSERT INTO PK_EPIZOD_ELEMENTY_HISTORIA"):
            self.insert_parameters = parameters
            return SimpleNamespace(fetchone=lambda: None)
        raise AssertionError(f"Nieobsługiwany SQL w teście: {sql}")


class FakeSyncConnection:
    def __init__(self):
        self.task = {
            "zadanie_id": 10,
            "data_zaplanowana": "2026-07-12 10:00:00",
            "data_realizacji": "2026-07-12 10:00:00",
            "eskulap_system": "ESKULAP",
            "eskulap_id": "901",
            "eskulap_pracownik": "Lekarz Testowy",
            "eskulap_data_wizyty": "2026-07-12 10:00:00",
            "eskulap_rodzaj_wizyty": "Wizyta laryngologiczna",
            "eskulap_decyzja": "J",
        }
        self.history_inserted = False

    def execute(self, sql, parameters=()):
        normalized = " ".join(sql.split()).upper()
        if normalized.startswith("SELECT * FROM PK_ZADANIA"):
            return SimpleNamespace(fetchone=lambda: dict(self.task))
        if normalized.startswith("UPDATE PK_ZADANIA"):
            for field in (
                "data_zaplanowana",
                "data_realizacji",
                "eskulap_system",
                "eskulap_id",
                "eskulap_pracownik",
                "eskulap_data_wizyty",
                "eskulap_rodzaj_wizyty",
                "eskulap_decyzja",
            ):
                self.task[field] = None
            return SimpleNamespace(fetchone=lambda: None)
        if normalized.startswith("SELECT * FROM PK_EPIZOD_ELEMENTY"):
            return SimpleNamespace(
                fetchone=lambda: {
                    "epizod_element_id": parameters[0],
                    "epizod_id": 77,
                }
            )
        if normalized.startswith("INSERT INTO PK_EPIZOD_ELEMENTY_HISTORIA"):
            self.history_inserted = True
            return SimpleNamespace(fetchone=lambda: None)
        raise AssertionError(f"Nieobsługiwany SQL w teście: {sql}")


def test_single_visit_single_block():
    assignments = match_visits_to_elements(
        [element(1, "KONSULTACJA_PSYCHIATRYCZNA", 1)],
        [visit(101, "F21", "2026-07-01T10:00:00")],
        {"F21": "KONSULTACJA_PSYCHIATRYCZNA"},
    )
    assert len(assignments) == 1
    assert assignments[0][0]["epizod_element_id"] == 1
    assert assignments[0][1].oracle_id == "101"


def test_many_visits_many_blocks_chronologically():
    assignments = match_visits_to_elements(
        [
            element(1, "SESJA_TERAPEUTYCZNA", 1),
            element(2, "SESJA_TERAPEUTYCZNA", 2),
        ],
        [
            visit(202, "F35", "2026-07-03T10:00:00"),
            visit(201, "F35", "2026-07-02T10:00:00"),
        ],
        {"F35": "SESJA_TERAPEUTYCZNA"},
    )
    assert [row[0]["epizod_element_id"] for row in assignments] == [1, 2]
    assert [row[1].oracle_id for row in assignments] == ["201", "202"]


def test_no_mapping_no_assignment():
    assignments = match_visits_to_elements(
        [element(1, "SESJA_TERAPEUTYCZNA", 1)],
        [visit(301, "XXX", "2026-07-02T10:00:00")],
        {"F35": "SESJA_TERAPEUTYCZNA"},
    )
    assert assignments == []


def test_pkk_kwal_not_auto_matched_again():
    assignments = match_visits_to_elements(
        [element(1, PKK_KWAL_BLOCK_CODE, 1)],
        [visit(501, "F18", "2026-07-01T09:00:00")],
        {"F18": PKK_KWAL_BLOCK_CODE},
    )
    assert assignments == []


def test_idempotency_skips_already_linked_element():
    assignments = match_visits_to_elements(
        [
            element(1, "KONSULTACJA_PSYCHIATRYCZNA", 1, eskulap_id="101"),
            element(2, "KONSULTACJA_PSYCHIATRYCZNA", 2),
        ],
        [visit(101, "F21", "2026-07-01T10:00:00")],
        {"F21": "KONSULTACJA_PSYCHIATRYCZNA"},
        {("ESKULAP", "101")},
    )
    assert assignments == []


def test_consultation_matches_first_free_consultation_block():
    assignments = match_consultations_to_elements(
        [
            element(1, "BADANIE_LAB", 1),
            element(2, "KONSULTACJA_SPECJALISTYCZNA", 2),
            element(3, "KONSULTACJA_SPECJALISTYCZNA", 3),
        ],
        [
            consultation(602, "2026-07-03T10:00:00"),
            consultation(601, "2026-07-02T10:00:00"),
        ],
    )
    assert [row[0]["epizod_element_id"] for row in assignments] == [2, 3]
    assert [row[1].oracle_id for row in assignments] == ["601", "602"]


def test_visit_does_not_match_specialist_consultation_block():
    assignments = match_visits_to_elements(
        [element(1, "KONSULTACJA_SPECJALISTYCZNA", 1)],
        [visit(901, "F99", "2026-07-01T10:00:00")],
        {"F99": "KONSULTACJA_SPECJALISTYCZNA"},
    )
    assert assignments == []


def test_consultation_does_not_match_visit_based_consultation_block():
    assignments = match_consultations_to_elements(
        [
            element(1, "KONSULTACJA_PSYCHIATRYCZNA_KOMPLEKSOWA", 1),
            element(2, "KONSULTACJA_SPECJALISTYCZNA", 2),
        ],
        [consultation(902, "2026-07-02T10:00:00")],
    )
    assert len(assignments) == 1
    assert assignments[0][0]["klocek_kod"] == "KONSULTACJA_SPECJALISTYCZNA"


def test_invalid_specialist_consultation_visit_assignment_is_cleared():
    connection = FakeSyncConnection()
    element_row = element(77, "KONSULTACJA_SPECJALISTYCZNA", 1, eskulap_id="901")
    element_row["zadanie_id"] = 10
    element_row["eskulap_system"] = "ESKULAP"

    changed = EpisodeSynchronizationService(
        gateway=SimpleNamespace()
    )._clear_invalid_specialist_consultation_assignment(
        connection,
        element_row,
    )

    assert changed
    assert connection.task["eskulap_system"] is None
    assert connection.task["eskulap_id"] is None
    assert connection.task["data_realizacji"] is None
    assert connection.history_inserted


def test_planned_eskulap_visit_is_planned_status():
    state = EpisodeStateService()._calculate_element_state(
        {
            "epizod_element_id": 1,
            "zadanie_id": 1,
            "lp": 1,
            "czy_aktywny": 1,
            "klocek_kod": "KONSULTACJA_SPECJALISTYCZNA",
            "status_cache": None,
            "data_zaplanowana": "2026-07-12 10:00:00",
            "data_realizacji": None,
            "eskulap_id": "601",
            "eskulap_decyzja": None,
            "eskulap_data_wizyty": "2026-07-12 10:00:00",
            "data_wymagana_do": None,
        }
    )
    assert state["status_wyliczony"] == STATUS_PLANNED


def test_record_history_fetches_episode_when_payload_is_task_only():
    connection = FakeConnection()
    record_history(
        connection,
        123,
        "EDYCJA",
        before={"zadanie": {"zadanie_id": 1}},
        after={"zadanie": {"zadanie_id": 1, "eskulap_id": "601"}},
        reason="Test synchronizacji",
        user_id="SYSTEM",
    )
    assert connection.insert_parameters[0] == 123
    assert connection.insert_parameters[1] == 77


def test_event_repository_maps_planned_visit_date():
    original = event_repository._get_patient_visits
    try:
        event_repository._get_patient_visits = lambda *args: [
            {
                "wizyta_id": 700,
                "pacjent_id": "P1",
                "data_wizyty": None,
                "data_planowana": "2026-07-12 10:00:00",
                "decyzja": None,
                "parametr_kod": "F21",
                "parametr_nazwa": "Wizyta planowana",
            }
        ]
        events = event_repository.get_patient_visits("P1")
    finally:
        event_repository._get_patient_visits = original

    assert len(events) == 1
    assert events[0].event_date is None
    assert events[0].planned_date == "2026-07-12 10:00:00"


def test_event_repository_maps_legacy_visit_planned_date():
    original = event_repository._get_patient_visits
    try:
        event_repository._get_patient_visits = lambda *args: [
            {
                "wizyta_id": 701,
                "pacjent_id": "P1",
                "data_wizyty": None,
                "data_wizyty_do": "2026-07-13 11:00:00",
                "decyzja": None,
                "parametr_kod": "F21",
                "parametr_nazwa": "Wizyta planowana",
            }
        ]
        events = event_repository.get_patient_visits("P1")
    finally:
        event_repository._get_patient_visits = original

    assert len(events) == 1
    assert events[0].event_date is None
    assert events[0].planned_date == "2026-07-13 11:00:00"


def test_event_repository_maps_planned_consultation_without_realization():
    original = event_repository._get_patient_consultations
    try:
        event_repository._get_patient_consultations = lambda *args: [
            {
                "konsultacja_id": 800,
                "pacjent_id": "P1",
                "data_przyjecia": None,
                "data_konsultacji": "2026-07-12 10:00:00",
                "data_planowana": "2026-07-12 10:00:00",
                "status": None,
            }
        ]
        events = event_repository.get_patient_consultations("P1")
    finally:
        event_repository._get_patient_consultations = original

    assert len(events) == 1
    assert events[0].event_date is None
    assert events[0].planned_date == "2026-07-12 10:00:00"


def test_event_repository_keeps_consultation_without_dates():
    original = event_repository._get_patient_consultations
    try:
        event_repository._get_patient_consultations = lambda *args: [
            {
                "konsultacja_id": 801,
                "pacjent_id": "P1",
                "data_przyjecia": None,
                "data_konsultacji": None,
                "data_planowana": None,
                "opis": "Konsultacja bez wyznaczonego terminu",
                "status": None,
            }
        ]
        events = event_repository.get_patient_consultations("P1")
    finally:
        event_repository._get_patient_consultations = original

    assert len(events) == 1
    assert events[0].event_date is None
    assert events[0].planned_date is None
    assert events[0].description == "Konsultacja bez wyznaczonego terminu"


def main():
    test_single_visit_single_block()
    test_many_visits_many_blocks_chronologically()
    test_no_mapping_no_assignment()
    test_pkk_kwal_not_auto_matched_again()
    test_idempotency_skips_already_linked_element()
    test_consultation_matches_first_free_consultation_block()
    test_visit_does_not_match_specialist_consultation_block()
    test_consultation_does_not_match_visit_based_consultation_block()
    test_invalid_specialist_consultation_visit_assignment_is_cleared()
    test_planned_eskulap_visit_is_planned_status()
    test_record_history_fetches_episode_when_payload_is_task_only()
    test_event_repository_maps_planned_visit_date()
    test_event_repository_maps_legacy_visit_planned_date()
    test_event_repository_maps_planned_consultation_without_realization()
    test_event_repository_keeps_consultation_without_dates()
    print("OK: logika synchronizacji epizodow")


if __name__ == "__main__":
    main()
