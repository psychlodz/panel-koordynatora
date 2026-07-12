from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.episode_synchronization_service import (
    PKK_KWAL_BLOCK_CODE,
    match_visits_to_elements,
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


def element(element_id, block_code, lp, eskulap_id=None):
    return {
        "epizod_element_id": element_id,
        "klocek_kod": block_code,
        "lp": lp,
        "eskulap_id": eskulap_id,
    }


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


def main():
    test_single_visit_single_block()
    test_many_visits_many_blocks_chronologically()
    test_no_mapping_no_assignment()
    test_pkk_kwal_not_auto_matched_again()
    test_idempotency_skips_already_linked_element()
    print("OK: logika synchronizacji epizodow")


if __name__ == "__main__":
    main()
