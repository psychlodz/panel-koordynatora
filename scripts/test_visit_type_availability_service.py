from pathlib import Path
from types import SimpleNamespace
import types
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

sys.modules.setdefault(
    "oracledb",
    types.SimpleNamespace(connect=lambda *args, **kwargs: None),
)

from app.models.work_schedule import VisitTypeAvailabilityRecord
from app.services.schedule_service import (
    build_visit_type_date_range_calendar,
    build_visit_type_month_calendar,
    merge_time_ranges,
)


def record(
    code,
    name,
    day,
    worker,
    start,
    end,
    pln_id,
    worker_id=None,
):
    return VisitTypeAvailabilityRecord(
        jo_id=249,
        jo_symbol="PKK",
        jo_nazwa="Punkt Konsultacyjny",
        data_dnia=f"2026-07-{day:02d}",
        pracownik_id=worker_id or worker,
        pracownik=worker,
        pln_id=pln_id,
        plw_id=f"{pln_id}-{code}",
        parametr_kod=code,
        parametr_nazwa=name,
        godz_od=start,
        godz_do=end,
        minuta_od=int(start[:2]) * 60 + int(start[3:5]),
        minuta_do=int(end[:2]) * 60 + int(end[3:5]),
    )


def first_cell(calendar, code, day):
    row = next(item for item in calendar["rows"] if item["code"] == code)
    return row["cells"][calendar["days"][day - 1]]


def test_overlapping_ranges_are_merged():
    calendar = build_visit_type_month_calendar(
        [
            record("F1", "Wizyta F1", 1, "Jan Kowalski", "08:00", "12:00", 1),
            record("F01", "Wizyta F1", 1, "Anna Nowak", "10:00", "14:00", 2),
        ],
        2026,
        7,
    )
    cell = first_cell(calendar, "F01", 1)
    assert cell["text"] == "08:00–14:00"
    assert len(cell["details"]) == 2


def test_touching_ranges_are_merged():
    assert merge_time_ranges([(8 * 60, 10 * 60), (10 * 60, 12 * 60)]) == [
        (8 * 60, 12 * 60)
    ]


def test_disjoint_ranges_stay_separate():
    calendar = build_visit_type_month_calendar(
        [
            record("F02", "Wizyta F2", 2, "Jan Kowalski", "08:00", "10:00", 1),
            record("F02", "Wizyta F2", 2, "Anna Nowak", "12:00", "15:00", 2),
        ],
        2026,
        7,
    )
    assert first_cell(calendar, "F02", 2)["text"] == "08:00–10:00\n12:00–15:00"


def test_one_worker_many_visit_types_is_one_popup_row():
    calendar = build_visit_type_month_calendar(
        [
            record("F03", "Konsultacja diagnostyczna", 3, "Jan Kowalski", "08:00", "12:00", 1),
            record("F04", "Sesja psychologiczna", 3, "Jan Kowalski", "08:00", "12:00", 1),
        ],
        2026,
        7,
    )
    cell = first_cell(calendar, "F03", 3)
    assert len(cell["details"]) == 1
    assert cell["details"][0]["rodzaje_wizyt"] == (
        "Konsultacja diagnostyczna\nSesja psychologiczna"
    )


def test_two_workers_are_two_popup_rows():
    calendar = build_visit_type_month_calendar(
        [
            record("F05", "Wizyta F5", 4, "Jan Kowalski", "08:00", "12:00", 1),
            record("F05", "Wizyta F5", 4, "Anna Nowak", "08:00", "12:00", 2),
        ],
        2026,
        7,
    )
    assert len(first_cell(calendar, "F05", 4)["details"]) == 2


def test_two_ranges_of_one_worker_are_two_popup_rows():
    calendar = build_visit_type_month_calendar(
        [
            record("F06", "Wizyta F6", 5, "Jan Kowalski", "08:00", "10:00", 1),
            record("F06", "Wizyta F6", 5, "Jan Kowalski", "12:00", "14:00", 2),
        ],
        2026,
        7,
    )
    assert len(first_cell(calendar, "F06", 5)["details"]) == 2


def test_missing_name_uses_code_and_message():
    calendar = build_visit_type_month_calendar(
        [record("F7", None, 6, "Jan Kowalski", "08:00", "10:00", 1)],
        2026,
        7,
    )
    row = next(item for item in calendar["rows"] if item["code"] == "F07")
    assert row["name"] == "F07 — brak nazwy rodzaju wizyty"
    assert "F07 — brak nazwy rodzaju wizyty" in first_cell(calendar, "F07", 6)["details"][0]["rodzaje_wizyt"]


def test_month_has_correct_number_of_days():
    february = build_visit_type_month_calendar([], 2028, 2)
    april = build_visit_type_month_calendar([], 2026, 4)
    assert len(february["days"]) == 29
    assert len(april["days"]) == 30


def test_date_range_can_cover_multiple_months():
    calendar = build_visit_type_date_range_calendar(
        [],
        "2026-07-15",
        "2026-09-14",
    )
    assert len(calendar["days"]) == 62
    assert calendar["days"][0].isoformat() == "2026-07-15"
    assert calendar["days"][-1].isoformat() == "2026-09-14"


def test_can_show_empty_dictionary_rows():
    calendar = build_visit_type_month_calendar(
        [],
        2026,
        7,
        only_available=False,
        visit_parameters=[
            SimpleNamespace(code="F1", name="Wizyta F1"),
            SimpleNamespace(code="F18", name="Wizyta F18"),
        ],
    )
    assert [row["code"] for row in calendar["rows"]] == ["F01", "F18"]


def main():
    test_overlapping_ranges_are_merged()
    test_touching_ranges_are_merged()
    test_disjoint_ranges_stay_separate()
    test_one_worker_many_visit_types_is_one_popup_row()
    test_two_workers_are_two_popup_rows()
    test_two_ranges_of_one_worker_are_two_popup_rows()
    test_missing_name_uses_code_and_message()
    test_month_has_correct_number_of_days()
    test_date_range_can_cover_multiple_months()
    test_can_show_empty_dictionary_rows()
    print("OK: test_visit_type_availability_service")


if __name__ == "__main__":
    main()
