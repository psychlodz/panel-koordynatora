from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.episode_state_service import (
    EpisodeStateService,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_PLANNED,
    STATUS_TO_PLAN,
    datetime_value,
)


def element(**values):
    row = {
        "epizod_element_id": 1,
        "zadanie_id": 1,
        "lp": 1,
        "czy_aktywny": 1,
        "klocek_kod": "KONSULTACJA_SPECJALISTYCZNA",
        "status_cache": None,
        "data_zaplanowana": None,
        "data_realizacji": None,
        "kompas_plan_data": None,
        "kompas_plan_godz_od": None,
        "eskulap_plan_data": None,
        "eskulap_id": None,
        "eskulap_system": None,
        "eskulap_decyzja": None,
        "eskulap_data_wizyty": None,
        "data_wymagana_do": None,
    }
    row.update(values)
    return row


def test_pkk_kwal_always_completed():
    state = EpisodeStateService()._calculate_element_state(
        element(klocek_kod="PKK_KWAL")
    )
    assert state["status_wyliczony"] == STATUS_COMPLETED


def test_planned_without_realization():
    state = EpisodeStateService()._calculate_element_state(
        element(data_zaplanowana="2026-07-12 10:00:00")
    )
    assert state["status_wyliczony"] == STATUS_PLANNED


def test_consultation_eskulap_planned_date_is_to_plan():
    state = EpisodeStateService()._calculate_element_state(
        element(
            eskulap_id="601",
            eskulap_system="ESKULAP_KONSULTACJE",
            eskulap_plan_data="2026-07-12 10:00:00",
        )
    )
    assert state["status_wyliczony"] == STATUS_TO_PLAN


def test_imaging_eskulap_planned_date_is_to_plan():
    state = EpisodeStateService()._calculate_element_state(
        element(
            klocek_kod="BADANIE_OBRAZOWE",
            eskulap_id="701",
            eskulap_system="ESKULAP_BADANIA_OBRAZOWE",
            eskulap_plan_data="2026-07-12 10:00:00",
        )
    )
    assert state["status_wyliczony"] == STATUS_TO_PLAN


def test_visit_block_planned_date_still_means_planned():
    state = EpisodeStateService()._calculate_element_state(
        element(
            klocek_kod="KONSULTACJA_PSYCHIATRYCZNA_KOMPLEKSOWA",
            eskulap_id="801",
            eskulap_system="ESKULAP",
            data_zaplanowana="2026-07-12 10:00:00",
        )
    )
    assert state["status_wyliczony"] == STATUS_PLANNED


def test_completed_from_decision_j():
    state = EpisodeStateService()._calculate_element_state(
        element(
            eskulap_id="123",
            eskulap_decyzja="J",
            data_realizacji="2026-07-12 10:00:00",
        )
    )
    assert state["status_wyliczony"] == STATUS_COMPLETED


def test_completed_from_realization_date_without_decision():
    state = EpisodeStateService()._calculate_element_state(
        element(
            eskulap_id="123",
            eskulap_decyzja=None,
            data_realizacji="2026-07-12 10:00:00",
        )
    )
    assert state["status_wyliczony"] == STATUS_COMPLETED


def test_cancelled_from_decision_b():
    state = EpisodeStateService()._calculate_element_state(
        element(
            eskulap_id="123",
            eskulap_decyzja="B",
            eskulap_data_wizyty="2026-07-12 10:00:00",
        )
    )
    assert state["status_wyliczony"] == STATUS_CANCELLED


def test_missing_visit_to_plan():
    state = EpisodeStateService()._calculate_element_state(element())
    assert state["status_wyliczony"] == STATUS_TO_PLAN


def test_next_task_is_first_active_to_plan_or_planned():
    service = EpisodeStateService()
    rows = [
        service._calculate_element_state(
            element(lp=1, eskulap_id="1", eskulap_decyzja="J", data_realizacji="2026-07-01")
        ),
        service._calculate_element_state(
            element(lp=2, epizod_element_id=2, zadanie_id=2)
        ),
        service._calculate_element_state(
            element(lp=3, epizod_element_id=3, zadanie_id=3, data_zaplanowana="2026-07-15")
        ),
    ]
    assert service._next_task(rows)["epizod_element_id"] == 2


def test_episode_state_service_does_not_use_oracle():
    source = Path("app/services/episode_state_service.py").read_text(
        encoding="utf-8"
    )
    forbidden = ("EskulapGateway", "oracledb", "app.gateway")
    assert not any(token in source for token in forbidden)


def test_synchronization_service_does_not_calculate_statuses():
    source = Path("app/services/episode_synchronization_service.py").read_text(
        encoding="utf-8"
    )
    assert "def status_from_visit" not in source
    assert "SET status =" not in source


def test_dashboard_and_details_use_episode_state_service():
    dashboard_repository = Path(
        "app/repositories/episode_dashboard_repository.py"
    ).read_text(encoding="utf-8")
    details_window = Path("app/ui/episode_details_window.py").read_text(
        encoding="utf-8"
    )
    assert "EpisodeStateService" in dashboard_repository
    assert "EpisodeStateService" in details_window
    assert "calculate_episode_state" in details_window


def test_dashboard_synchronizes_on_open():
    dashboard_window = Path("app/ui/episodes_dashboard_window.py").read_text(
        encoding="utf-8"
    )
    assert "self.synchronize_and_refresh()" in dashboard_window
    assert "EpisodeSynchronizationService().synchronize(epizod_ids)" in dashboard_window
    assert "EpisodeStateService().calculate_all_episode_states()" in dashboard_window


def test_datetime_value_parses_datetime_strings():
    assert datetime_value("2026-07-12 10:00:00").year == 2026


def main():
    test_pkk_kwal_always_completed()
    test_planned_without_realization()
    test_consultation_eskulap_planned_date_is_to_plan()
    test_imaging_eskulap_planned_date_is_to_plan()
    test_visit_block_planned_date_still_means_planned()
    test_completed_from_decision_j()
    test_completed_from_realization_date_without_decision()
    test_cancelled_from_decision_b()
    test_missing_visit_to_plan()
    test_next_task_is_first_active_to_plan_or_planned()
    test_episode_state_service_does_not_use_oracle()
    test_synchronization_service_does_not_calculate_statuses()
    test_dashboard_and_details_use_episode_state_service()
    test_dashboard_synchronizes_on_open()
    test_datetime_value_parses_datetime_strings()
    print("OK: test_episode_state_service")


if __name__ == "__main__":
    main()
