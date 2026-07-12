from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ui.episode_details_presenter import (
    eskulap_visit_details,
    process_element_label,
    process_element_tooltip,
    status_with_date,
)


def test_process_element_label_contains_deadline():
    text = process_element_label(
        {
            "nazwa_w_sciezce": "Konsultacja psychiatryczna",
            "data_wymagana_do": "2026-07-20",
            "czy_aktywny": 1,
        }
    )
    assert text == (
        "Konsultacja psychiatryczna\n"
        "Data realizacji do: 2026-07-20"
    )


def test_missing_deadline_is_brak():
    text = process_element_label(
        {
            "nazwa_w_sciezce": "Konsultacja psychiatryczna",
            "data_wymagana_do": None,
            "czy_aktywny": 1,
        }
    )
    assert text.endswith("Data realizacji do: brak")


def test_auto_duplicate_label_is_visible():
    record = {
        "nazwa_w_sciezce": "Badanie obrazowe",
        "data_wymagana_do": None,
        "czy_aktywny": 1,
        "typ_pochodzenia": "POWIELENIE_AUTOMATYCZNE",
        "element_zrodlowy_id": 10,
        "eskulap_system": "ESKULAP_BADANIA_OBRAZOWE",
        "eskulap_id": "IMG-1",
    }
    text = process_element_label(record)
    tooltip = process_element_tooltip(record)
    assert "Powielenie z Eskulap" in text
    assert "Element źródłowy: 10" in tooltip
    assert "ESKULAP_BADANIA_OBRAZOWE / IMG-1" in tooltip


def test_status_with_date_for_realized():
    text = status_with_date(
        {
            "status": "ZREALIZOWANA",
            "data_realizacji": "2026-07-10 12:30:00",
        }
    )
    assert text == "ZREALIZOWANA\n2026-07-10 12:30"


def test_eskulap_details_do_not_show_date():
    text = eskulap_visit_details(
        {
            "eskulap_pracownik": "Nowak Anna",
            "eskulap_data_wizyty": "2026-07-10 12:30:00",
            "eskulap_rodzaj_wizyty": "Wizyta kwalifikacyjna PKK",
        }
    )
    assert text == "Nowak Anna\nWizyta kwalifikacyjna PKK"
    assert "2026-07-10" not in text


def test_missing_eskulap_details_are_brak():
    assert eskulap_visit_details({}) == "brak"


def test_consultation_description_is_visible_without_worker():
    text = eskulap_visit_details(
        {
            "eskulap_pracownik": None,
            "eskulap_rodzaj_wizyty": "Konsultacja bez wyznaczonego terminu",
        }
    )
    assert text == "Konsultacja bez wyznaczonego terminu"
    assert "brak" not in text


def test_window_has_no_bottom_tabs_and_uses_main_table_selection():
    source = Path("app/ui/episode_details_window.py").read_text(encoding="utf-8")
    assert "QTabWidget" not in source
    assert "self.tabs" not in source
    assert "_process_tasks_table" not in source
    assert "EpisodeSynchronizationService().synchronize_episode" in source
    selection_start = source.index("def _selected_episode_element_id")
    selection_end = source.index(
        "\n    def _selected_episode_element(",
        selection_start,
    )
    selection_body = source[selection_start:selection_end]
    assert "_process_overview_table" in selection_body
    assert "_process_tasks_table" not in selection_body


def main():
    test_process_element_label_contains_deadline()
    test_missing_deadline_is_brak()
    test_auto_duplicate_label_is_visible()
    test_status_with_date_for_realized()
    test_eskulap_details_do_not_show_date()
    test_missing_eskulap_details_are_brak()
    test_consultation_description_is_visible_without_worker()
    test_window_has_no_bottom_tabs_and_uses_main_table_selection()
    print("OK: test_episode_details_presenter")


if __name__ == "__main__":
    main()
