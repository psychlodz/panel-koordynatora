from __future__ import annotations

from collections import defaultdict
from contextlib import closing
from dataclasses import dataclass
from datetime import date, datetime

from app.repositories.db_connection import (
    create_connection,
    initialize_database,
    patient_id_column,
)


STATUS_TO_PLAN = "DO_ZAPLANOWANIA"
STATUS_PLANNED = "ZAPLANOWANA"
STATUS_COMPLETED = "ZREALIZOWANA"
STATUS_CANCELLED = "ANULOWANA"
PKK_KWAL_BLOCK_CODE = "PKK_KWAL"
SOURCE_CONSULTATION = "ESKULAP_KONSULTACJE"
SOURCE_IMAGING = "ESKULAP_BADANIA_OBRAZOWE"
SPECIALIST_CONSULTATION_BLOCK_CODES = {"KONSULTACJA_SPECJALISTYCZNA"}
IMAGING_BLOCK_CODES = {"BADANIE_OBRAZOWE"}

NEXT_TASK_STATUSES = {STATUS_TO_PLAN, STATUS_PLANNED}
COMPLETED_STATUSES = {STATUS_COMPLETED, "ZREALIZOWANO", "ZREALIZOWANE"}
CANCELLED_STATUSES = {STATUS_CANCELLED, "ANULOWANO", "ANULOWANE"}


@dataclass(frozen=True)
class EpisodeProgress:
    total: int
    completed: int
    percent: float


def normalized_status(value):
    return str(value or "").strip().upper()


def date_value(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError:
        return None


def datetime_value(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _is_external_manual_planning_element(row):
    block_code = str(row.get("klocek_kod") or "").strip().upper()
    source = str(row.get("eskulap_system") or "").strip().upper()
    return (
        block_code in SPECIALIST_CONSULTATION_BLOCK_CODES
        or block_code in IMAGING_BLOCK_CODES
        or source in {SOURCE_CONSULTATION, SOURCE_IMAGING}
    )


class EpisodeStateService:
    """Centralne miejsce wyliczania bieżącego stanu epizodu KOMPAS.

    Usługa korzysta wyłącznie z PostgreSQL. Nie odwołuje się do Oracle ani do
    warstwy integracyjnej Eskulapa.
    """

    def calculate_episode_state(self, epizod_id, update_cache=True):
        initialize_database()
        with closing(create_connection()) as connection:
            with connection:
                episode = self._get_episode(connection, epizod_id)
                if episode is None:
                    raise ValueError(f"Nie znaleziono epizodu o ID {epizod_id}")
                elements = self._episode_elements(connection, epizod_id)
                calculated = [
                    self._calculate_element_state(element)
                    for element in elements
                ]
                if update_cache:
                    self._update_task_status_cache(connection, calculated)
                progress = self._progress(calculated)
                next_task = self._next_task(calculated)
                summary = self._episode_summary(
                    episode,
                    calculated,
                    progress,
                    next_task,
                )
                return {
                    "episode": summary,
                    "elements": calculated,
                    "progress": {
                        "liczba_zadan": progress.total,
                        "liczba_zrealizowanych_zadan": progress.completed,
                        "procent_realizacji": progress.percent,
                    },
                    "next_task": next_task,
                }

    def calculate_all_episode_states(self, update_cache=True):
        initialize_database()
        with closing(create_connection()) as connection:
            with connection:
                episodes = self._list_episodes(connection)
                elements_by_episode = self._all_episode_elements(connection)
                result = []
                all_calculated = []
                for episode in episodes:
                    calculated = [
                        self._calculate_element_state(element)
                        for element in elements_by_episode.get(
                            episode["epizod_id"],
                            [],
                        )
                    ]
                    all_calculated.extend(calculated)
                    progress = self._progress(calculated)
                    next_task = self._next_task(calculated)
                    result.append(
                        self._episode_summary(
                            episode,
                            calculated,
                            progress,
                            next_task,
                        )
                    )
                if update_cache:
                    self._update_task_status_cache(connection, all_calculated)
                return result

    def calculate_next_task(self, epizod_id):
        return self.calculate_episode_state(epizod_id)["next_task"]

    def calculate_progress(self, epizod_id):
        return self.calculate_episode_state(epizod_id)["progress"]

    def get_episode_summary(self, epizod_id):
        return self.calculate_episode_state(epizod_id)["episode"]

    def calculate_dashboard_counters(self, episodes=None):
        episodes = (
            episodes
            if episodes is not None
            else self.calculate_all_episode_states()
        )
        return {
            "active_episodes": sum(row["is_active"] for row in episodes),
            "episodes_to_plan": sum(row["has_to_plan"] for row in episodes),
            "overdue_episodes": sum(row["has_overdue"] for row in episodes),
            "tasks_scheduled_today": sum(
                row["scheduled_today_count"] for row in episodes
            ),
            "waiting_for_eskulap": sum(
                row["waiting_for_eskulap"] for row in episodes
            ),
            "completed_this_month": sum(
                row["completed_this_month"] for row in episodes
            ),
        }

    def _get_episode(self, connection, epizod_id):
        row = connection.execute(
            f"""
            SELECT
                e.epizod_id,
                {patient_id_column("e")} AS pacjent_id,
                e.program_id,
                e.sciezka_id,
                e.data_start,
                e.data_zakonczenia,
                e.status,
                e.koordynator_id,
                e.source_system,
                e.source_type,
                e.source_id,
                p.kod AS program_kod,
                p.nazwa AS program_nazwa,
                s.kod AS sciezka_kod,
                s.nazwa AS sciezka_nazwa
            FROM pk_epizody e
            LEFT JOIN pk_programy p ON p.program_id = e.program_id
            LEFT JOIN pk_sciezki s ON s.sciezka_id = e.sciezka_id
            WHERE e.epizod_id = ?
            """,
            (epizod_id,),
        ).fetchone()
        return dict(row) if row is not None else None

    def _list_episodes(self, connection):
        rows = connection.execute(
            f"""
            SELECT
                e.epizod_id,
                {patient_id_column("e")} AS pacjent_id,
                e.program_id,
                e.sciezka_id,
                e.data_start,
                e.data_zakonczenia,
                e.status,
                e.koordynator_id,
                e.source_system,
                e.source_type,
                e.source_id,
                p.kod AS program_kod,
                p.nazwa AS program_nazwa,
                s.kod AS sciezka_kod,
                s.nazwa AS sciezka_nazwa
            FROM pk_epizody e
            LEFT JOIN pk_programy p ON p.program_id = e.program_id
            LEFT JOIN pk_sciezki s ON s.sciezka_id = e.sciezka_id
            ORDER BY e.data_start DESC, e.epizod_id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def _episode_elements(self, connection, epizod_id):
        rows = connection.execute(
            self._episode_elements_sql() + " WHERE ep.epizod_id = ? "
            "ORDER BY ee.lp, ee.epizod_element_id, z.zadanie_id",
            (epizod_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def _all_episode_elements(self, connection):
        rows = connection.execute(
            self._episode_elements_sql()
            + " ORDER BY ep.epizod_id, ee.lp, ee.epizod_element_id, z.zadanie_id"
        ).fetchall()
        grouped = defaultdict(list)
        for row in rows:
            item = dict(row)
            grouped[item["epizod_id"]].append(item)
        return grouped

    @staticmethod
    def _episode_elements_sql():
        return """
            SELECT
                ep.epizod_id,
                ee.epizod_element_id,
                ee.sciezka_element_id AS element_id,
                ee.lp,
                ee.nazwa AS nazwa_w_sciezce,
                ee.czy_aktywny,
                ee.typ_pochodzenia,
                ee.powod_modyfikacji,
                k.kod AS klocek_kod,
                k.nazwa AS klocek_nazwa,
                k.kolor AS klocek_kolor,
                k.kolor_tekstu AS klocek_kolor_tekstu,
                z.zadanie_id,
                z.status AS status_cache,
                z.data_wymagana_do,
                z.data_zaplanowana,
                z.data_realizacji,
                z.kompas_plan_data,
                z.kompas_plan_godz_od,
                z.kompas_plan_godz_do,
                z.kompas_plan_uwagi,
                z.kompas_plan_user_id,
                z.zrodlo,
                z.eskulap_system,
                z.eskulap_id,
                z.eskulap_pracownik,
                z.eskulap_data_wizyty,
                z.eskulap_plan_data,
                z.eskulap_plan_godz_od,
                z.eskulap_plan_godz_do,
                z.eskulap_rodzaj_wizyty,
                z.eskulap_decyzja,
                z.uwagi,
                se.czy_wymaga_zlecenia
            FROM pk_epizody ep
            JOIN pk_epizod_elementy ee
                ON ee.epizod_id = ep.epizod_id
            JOIN pk_klocki k ON k.klocek_id = ee.klocek_id
            LEFT JOIN pk_sciezka_elementy se
                ON se.element_id = ee.sciezka_element_id
            LEFT JOIN pk_zadania z
                ON z.epizod_id = ep.epizod_id
               AND z.epizod_element_id = ee.epizod_element_id
        """

    def _calculate_element_state(self, element):
        row = dict(element)
        decision = str(row.get("eskulap_decyzja") or "").strip().upper()
        block_code = str(row.get("klocek_kod") or "").strip().upper()
        has_visit = bool(row.get("eskulap_id"))
        planned = row.get("data_zaplanowana")
        realized = row.get("data_realizacji")
        manual_planning_required = _is_external_manual_planning_element(row)

        if block_code == PKK_KWAL_BLOCK_CODE:
            status = STATUS_COMPLETED
            status_at = realized or row.get("eskulap_data_wizyty")
        elif decision == "B":
            status = STATUS_CANCELLED
            status_at = row.get("eskulap_data_wizyty") or realized
        elif realized:
            status = STATUS_COMPLETED
            status_at = realized
        elif manual_planning_required and planned:
            status = STATUS_PLANNED
            status_at = planned
        elif manual_planning_required:
            status = STATUS_TO_PLAN
            status_at = None
        elif planned and not realized:
            status = STATUS_PLANNED
            status_at = planned
        elif not has_visit:
            status = STATUS_TO_PLAN
            status_at = None
        else:
            status = STATUS_TO_PLAN
            status_at = None

        row["status"] = status
        row["status_wyliczony"] = status
        row["status_data_czas"] = status_at
        row["termin"] = planned or row.get("data_wymagana_do")
        return row

    def _update_task_status_cache(self, connection, elements):
        for element in elements:
            task_id = element.get("zadanie_id")
            if not task_id:
                continue
            current = normalized_status(element.get("status_cache"))
            calculated = normalized_status(element.get("status_wyliczony"))
            if current == calculated:
                continue
            connection.execute(
                """
                UPDATE pk_zadania
                SET status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE zadanie_id = ?
                """,
                (element["status_wyliczony"], task_id),
            )

    def _progress(self, elements):
        active = [
            element
            for element in elements
            if element.get("czy_aktywny") in (None, 1, True)
            and normalized_status(element["status_wyliczony"])
            not in CANCELLED_STATUSES
        ]
        completed = sum(
            normalized_status(element["status_wyliczony"])
            in COMPLETED_STATUSES
            for element in active
        )
        total = len(active)
        percent = round(100.0 * completed / total, 1) if total else 0.0
        return EpisodeProgress(total=total, completed=completed, percent=percent)

    def _next_task(self, elements):
        candidates = [
            element
            for element in elements
            if element.get("czy_aktywny") in (None, 1, True)
            and normalized_status(element["status_wyliczony"])
            in NEXT_TASK_STATUSES
        ]
        return min(
            candidates,
            key=lambda element: (
                int(element.get("lp") or 999999),
                date_value(element.get("termin")) is None,
                date_value(element.get("termin")) or date.max,
                int(element.get("zadanie_id") or 999999999),
            ),
            default=None,
        )

    def _episode_summary(self, episode, elements, progress, next_task):
        today = date.today()
        month_start = today.replace(day=1)
        active_elements = [
            element
            for element in elements
            if element.get("czy_aktywny") in (None, 1, True)
        ]
        has_to_plan = any(
            normalized_status(element["status_wyliczony"]) == STATUS_TO_PLAN
            for element in active_elements
        )
        has_overdue = any(
            normalized_status(element["status_wyliczony"])
            in NEXT_TASK_STATUSES
            and date_value(element.get("termin")) is not None
            and date_value(element.get("termin")) < today
            for element in active_elements
        )
        scheduled_today_count = sum(
            normalized_status(element["status_wyliczony"]) == STATUS_PLANNED
            and date_value(element.get("data_zaplanowana")) == today
            for element in active_elements
        )
        waiting_for_eskulap = any(
            bool(element.get("czy_wymaga_zlecenia"))
            and not element.get("eskulap_id")
            and normalized_status(element["status_wyliczony"]) == STATUS_TO_PLAN
            for element in active_elements
        )
        end_date = date_value(episode.get("data_zakonczenia"))
        completed_this_month = bool(
            end_date
            and month_start <= end_date <= today
        )
        is_active = end_date is None

        row = dict(episode)
        row.update(
            {
                "status": episode.get("status") or ("AKTYWNY" if is_active else ""),
                "liczba_zadan": progress.total,
                "liczba_zrealizowanych_zadan": progress.completed,
                "procent_realizacji": progress.percent,
                "next_task_id": next_task.get("zadanie_id") if next_task else None,
                "next_task_name": (
                    (
                        next_task.get("nazwa_w_sciezce")
                        or next_task.get("klocek_nazwa")
                    )
                    if next_task
                    else None
                ),
                "next_task_due": next_task.get("termin") if next_task else None,
                "next_task_status": (
                    next_task.get("status_wyliczony") if next_task else None
                ),
                "next_task_color": (
                    next_task.get("klocek_kolor") if next_task else None
                ),
                "next_task_text_color": (
                    next_task.get("klocek_kolor_tekstu") if next_task else None
                ),
                "is_active": is_active,
                "has_to_plan": has_to_plan,
                "has_overdue": has_overdue,
                "has_scheduled_today": scheduled_today_count > 0,
                "scheduled_today_count": scheduled_today_count,
                "waiting_for_eskulap": waiting_for_eskulap,
                "completed_this_month": completed_this_month,
            }
        )
        return row
