from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Iterable

from app.repositories.db_connection import create_connection, patient_id_column
from app.repositories.episode_element_repository import record_history


SYSTEM_USER = "SYSTEM"
SYNC_REASON = "Synchronizacja z Eskulap."
SOURCE_SYSTEM = "ESKULAP"
SOURCE_CONSULTATION = "ESKULAP_KONSULTACJE"
SOURCE_IMAGING = "ESKULAP_BADANIA_OBRAZOWE"
PKK_KWAL_BLOCK_CODE = "PKK_KWAL"
SPECIALIST_CONSULTATION_BLOCK_CODES = {"KONSULTACJA_SPECJALISTYCZNA"}
IMAGING_BLOCK_CODES = {"BADANIE_OBRAZOWE"}
AUTO_DUPLICATE_ORIGIN = "POWIELENIE_AUTOMATYCZNE"
AUTO_DUPLICATE_CONSULTATION_REASON = (
    "Automatyczne powielenie po synchronizacji z Eskulap — "
    "dodatkowa konsultacja specjalistyczna"
)
AUTO_DUPLICATE_IMAGING_REASON = (
    "Automatyczne powielenie po synchronizacji z Eskulap — "
    "dodatkowe zlecenie badania obrazowego"
)

STATUS_TO_PLAN = "DO_ZAPLANOWANIA"


@dataclass
class EpisodeSynchronizationSummary:
    episodes: int = 0
    visits: int = 0
    new_assignments: int = 0
    status_changes: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def error_count(self):
        return len(self.errors)


def _as_datetime(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.combine(date.fromisoformat(str(value)[:10]), time.min)
        except ValueError:
            return None


def _event_key(visit):
    return _event_source(visit), str(getattr(visit, "oracle_id", "") or "")


def _event_source(event):
    event_type = str(getattr(event, "event_type", "") or "").upper()
    source = str(getattr(event, "source", "") or "").upper()
    if event_type == "CONSULTATION" or "KONSULTACJE" in source:
        return SOURCE_CONSULTATION
    if event_type == "IMAGING_ORDER":
        return SOURCE_IMAGING
    return SOURCE_SYSTEM


def _decision(visit):
    return str(getattr(visit, "status", "") or "").strip().upper()


def mapped_block_code(visit, visit_mapping):
    code = str(getattr(visit, "parametr_kod", "") or "").strip().upper()
    return visit_mapping.get(code)


def is_specialist_consultation_block(block_code):
    return str(block_code or "").strip().upper() in SPECIALIST_CONSULTATION_BLOCK_CODES


def is_imaging_block(block_code):
    return str(block_code or "").strip().upper() in IMAGING_BLOCK_CODES


def _event_sort_key(event):
    return (
        _as_datetime(getattr(event, "event_date", None))
        or _as_datetime(getattr(event, "planned_date", None))
        or _as_datetime(getattr(event, "realization_date", None))
        or datetime.max,
        str(getattr(event, "oracle_id", "") or ""),
    )


def match_visits_to_elements(elements, visits, visit_mapping, used_visit_keys=None):
    """Chronologicznie przypisuje wizyty do pierwszych wolnych elementów.

    Jedna wizyta może trafić tylko do jednego elementu i jeden element może
    dostać najwyżej jedną wizytę.
    """
    free_elements_by_block = {}
    for element in sorted(
        elements,
        key=lambda row: (
            int(row.get("lp") or 0),
            int(row.get("epizod_element_id") or 0),
        ),
    ):
        if element.get("eskulap_id"):
            continue
        block_code = str(element.get("klocek_kod") or "").strip().upper()
        if (
            not block_code
            or block_code == PKK_KWAL_BLOCK_CODE
            or is_specialist_consultation_block(block_code)
        ):
            continue
        free_elements_by_block.setdefault(block_code, []).append(element)

    assignments = []
    used_visit_keys = set(used_visit_keys or set())
    sorted_visits = sorted(visits, key=_event_sort_key)
    for visit in sorted_visits:
        visit_key = _event_key(visit)
        if visit_key in used_visit_keys:
            continue
        block_code = mapped_block_code(visit, visit_mapping)
        if not block_code:
            continue
        candidates = free_elements_by_block.get(block_code, [])
        if not candidates:
            continue
        element = candidates.pop(0)
        used_visit_keys.add(visit_key)
        assignments.append((element, visit))
    return assignments


def match_events_to_elements(
    elements,
    events,
    block_codes,
    used_event_keys=None,
):
    free_elements = []
    block_codes = {
        str(block_code or "").strip().upper()
        for block_code in block_codes
    }
    for element in sorted(
        elements,
        key=lambda row: (
            int(row.get("lp") or 0),
            int(row.get("epizod_element_id") or 0),
        ),
    ):
        if element.get("eskulap_id"):
            continue
        block_code = str(element.get("klocek_kod") or "").strip().upper()
        if block_code in block_codes:
            free_elements.append(element)

    assignments = []
    used_event_keys = set(used_event_keys or set())
    for event in sorted(events, key=_event_sort_key):
        event_key = _event_key(event)
        if event_key in used_event_keys:
            continue
        if not free_elements:
            break
        element = free_elements.pop(0)
        used_event_keys.add(event_key)
        assignments.append((element, event))
    return assignments


def match_consultations_to_elements(elements, consultations, used_event_keys=None):
    return match_events_to_elements(
        elements,
        consultations,
        SPECIALIST_CONSULTATION_BLOCK_CODES,
        used_event_keys,
    )


class EpisodeSynchronizationService:
    def __init__(self, gateway=None):
        if gateway is None:
            from app.gateway.eskulap_gateway import EskulapGateway

            gateway = EskulapGateway()
        self.gateway = gateway

    def synchronize(self, epizod_ids=None) -> EpisodeSynchronizationSummary:
        summary = EpisodeSynchronizationSummary()
        with closing(create_connection()) as connection:
            with connection:
                episodes = self._list_active_episodes(connection, epizod_ids)
                summary.episodes = len(episodes)
                visit_mapping = self._visit_mapping(connection)
                globally_used_visits = self._used_visit_keys(connection)

                for episode in episodes:
                    try:
                        visits = self.gateway.get_patient_visits(
                            episode["pacjent_id"],
                            date_from=episode["data_start"],
                        )
                        consultations = self.gateway.get_patient_consultations(
                            episode["pacjent_id"],
                            date_from=episode["data_start"],
                        )
                        imaging_orders = self.gateway.get_patient_imaging_orders(
                            episode["pacjent_id"],
                            date_from=episode["data_start"],
                        )
                        summary.visits += (
                            len(visits)
                            + len(consultations)
                            + len(imaging_orders)
                        )
                        result = self._synchronize_episode(
                            connection,
                            episode,
                            visits,
                            consultations,
                            imaging_orders,
                            visit_mapping,
                            globally_used_visits,
                        )
                        summary.new_assignments += result["new_assignments"]
                    except Exception as exc:
                        summary.errors.append(
                            f"Epizod {episode['epizod_id']}: {exc}"
                        )
            return summary

    def synchronize_episode(self, epizod_id) -> EpisodeSynchronizationSummary:
        summary = EpisodeSynchronizationSummary()
        with closing(create_connection()) as connection:
            with connection:
                episode = self._get_active_episode(connection, epizod_id)
                if episode is None:
                    summary.errors.append(
                        f"Nie znaleziono aktywnego epizodu {epizod_id}."
                    )
                    return summary
                summary.episodes = 1
                visit_mapping = self._visit_mapping(connection)
                globally_used_visits = self._used_visit_keys(connection)
                try:
                    visits = self.gateway.get_patient_visits(
                        episode["pacjent_id"],
                        date_from=episode["data_start"],
                    )
                    consultations = self.gateway.get_patient_consultations(
                        episode["pacjent_id"],
                        date_from=episode["data_start"],
                    )
                    imaging_orders = self.gateway.get_patient_imaging_orders(
                        episode["pacjent_id"],
                        date_from=episode["data_start"],
                    )
                    summary.visits = (
                        len(visits)
                        + len(consultations)
                        + len(imaging_orders)
                    )
                    result = self._synchronize_episode(
                        connection,
                        episode,
                        visits,
                        consultations,
                        imaging_orders,
                        visit_mapping,
                        globally_used_visits,
                    )
                    summary.new_assignments = result["new_assignments"]
                except Exception as exc:
                    summary.errors.append(f"Epizod {epizod_id}: {exc}")
                    raise
            return summary

    def _list_active_episodes(self, connection, epizod_ids=None):
        conditions = ["data_zakonczenia IS NULL"]
        parameters = []
        if epizod_ids is not None:
            ids = sorted({int(value) for value in epizod_ids})
            if not ids:
                return []
            placeholders = ", ".join("?" for _ in ids)
            conditions.append(f"epizod_id IN ({placeholders})")
            parameters.extend(ids)
        where_clause = " AND ".join(conditions)
        rows = connection.execute(
            f"""
            SELECT
                epizod_id,
                {patient_id_column()} AS pacjent_id,
                data_start,
                source_system,
                source_type,
                source_id
            FROM pk_epizody
            WHERE {where_clause}
            ORDER BY data_start, epizod_id
            """,
            tuple(parameters),
        ).fetchall()
        return [dict(row) for row in rows]

    def _get_active_episode(self, connection, epizod_id):
        row = connection.execute(
            f"""
            SELECT
                epizod_id,
                {patient_id_column()} AS pacjent_id,
                data_start,
                source_system,
                source_type,
                source_id
            FROM pk_epizody
            WHERE epizod_id = ?
              AND data_zakonczenia IS NULL
            """,
            (epizod_id,),
        ).fetchone()
        return dict(row) if row is not None else None

    def _visit_mapping(self, connection):
        rows = connection.execute(
            """
            SELECT r.parametr_kod, k.kod AS klocek_kod
            FROM pk_mapowanie_wizyt m
            JOIN pk_rodzaje_wizyt_eskulap r
                ON r.rodzaj_wizyty_id = m.rodzaj_wizyty_id
            JOIN pk_klocki k ON k.klocek_id = m.klocek_id
            WHERE m.czy_aktywne = 1
              AND r.czy_aktywny_kompas = 1
              AND k.czy_aktywny = 1
            """
        ).fetchall()
        return {
            str(row["parametr_kod"]).strip().upper(): row["klocek_kod"]
            for row in rows
        }

    def _used_visit_keys(self, connection):
        rows = connection.execute(
            """
            SELECT eskulap_system, eskulap_id
            FROM pk_zadania
            WHERE eskulap_system IS NOT NULL
              AND eskulap_id IS NOT NULL
            """
        ).fetchall()
        keys = set()
        for row in rows:
            system = str(row["eskulap_system"])
            oracle_id = str(row["eskulap_id"])
            keys.add((system, oracle_id))
            if system != SOURCE_CONSULTATION:
                keys.add((SOURCE_SYSTEM, oracle_id))
        return keys

    def _episode_elements(self, connection, epizod_id):
        rows = connection.execute(
            """
            SELECT
                ee.epizod_element_id,
                ee.epizod_id,
                ee.sciezka_element_id AS element_id,
                ee.klocek_id,
                ee.element_zrodlowy_id,
                ee.lp,
                ee.nazwa,
                ee.typ_pochodzenia,
                k.kod AS klocek_kod,
                z.zadanie_id,
                z.status,
                z.data_zaplanowana,
                z.data_realizacji,
                z.eskulap_system,
                z.eskulap_id
            FROM pk_epizod_elementy ee
            JOIN pk_klocki k ON k.klocek_id = ee.klocek_id
            LEFT JOIN pk_zadania z
                ON z.epizod_element_id = ee.epizod_element_id
            WHERE ee.epizod_id = ?
              AND ee.czy_aktywny = 1
            ORDER BY ee.lp, ee.epizod_element_id, z.zadanie_id
            """,
            (epizod_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def _synchronize_episode(
        self,
        connection,
        episode,
        visits,
        consultations,
        imaging_orders,
        visit_mapping,
        globally_used_visits,
    ):
        result = {"new_assignments": 0}
        elements = self._episode_elements(connection, episode["epizod_id"])

        for element in elements:
            if str(element.get("klocek_kod") or "").upper() == PKK_KWAL_BLOCK_CODE:
                task_id = self._ensure_task(connection, episode, element)
                if self._update_task_from_visit(
                    connection,
                    task_id,
                    element,
                    self._qualification_visit(episode, visits),
                ):
                    result["new_assignments"] += 1

        for element in elements:
            self._clear_invalid_specialist_consultation_assignment(
                connection,
                element,
            )

        unused_visits = [
            visit
            for visit in visits
            if _event_key(visit) not in globally_used_visits
        ]
        for element, visit in match_visits_to_elements(
            elements,
            unused_visits,
            visit_mapping,
            globally_used_visits,
        ):
            task_id = self._ensure_task(connection, episode, element)
            if self._update_task_from_visit(connection, task_id, element, visit):
                globally_used_visits.add(_event_key(visit))
                result["new_assignments"] += 1

        unused_consultations = [
            consultation
            for consultation in consultations
            if _event_key(consultation) not in globally_used_visits
        ]
        elements = self._ensure_event_elements(
            connection,
            episode,
            elements,
            unused_consultations,
            SPECIALIST_CONSULTATION_BLOCK_CODES,
            AUTO_DUPLICATE_CONSULTATION_REASON,
        )
        for element, consultation in match_consultations_to_elements(
            elements,
            unused_consultations,
            globally_used_visits,
        ):
            task_id = self._ensure_task(connection, episode, element)
            if self._update_task_from_visit(
                connection,
                task_id,
                element,
                consultation,
            ):
                globally_used_visits.add(_event_key(consultation))
                result["new_assignments"] += 1

        unused_imaging_orders = [
            imaging_order
            for imaging_order in imaging_orders
            if _event_key(imaging_order) not in globally_used_visits
        ]
        elements = self._ensure_event_elements(
            connection,
            episode,
            elements,
            unused_imaging_orders,
            IMAGING_BLOCK_CODES,
            AUTO_DUPLICATE_IMAGING_REASON,
        )
        for element, imaging_order in match_events_to_elements(
            elements,
            unused_imaging_orders,
            IMAGING_BLOCK_CODES,
            globally_used_visits,
        ):
            task_id = self._ensure_task(connection, episode, element)
            if self._update_task_from_visit(
                connection,
                task_id,
                element,
                imaging_order,
            ):
                globally_used_visits.add(_event_key(imaging_order))
                result["new_assignments"] += 1
        return result

    def _qualification_visit(self, episode, visits):
        source_id = str(episode.get("source_id") or "")
        if source_id:
            for visit in visits:
                if str(getattr(visit, "oracle_id", "") or "") == source_id:
                    return visit
        return None

    def _ensure_event_elements(
        self,
        connection,
        episode,
        elements,
        events,
        block_codes,
        reason,
    ):
        events = list(events)
        if not events:
            return elements
        block_codes = {
            str(block_code or "").strip().upper()
            for block_code in block_codes
        }
        candidates = [
            element
            for element in elements
            if str(element.get("klocek_kod") or "").strip().upper()
            in block_codes
        ]
        if not candidates:
            return elements

        free_candidates = [
            element
            for element in candidates
            if not element.get("eskulap_id")
        ]
        missing = len(events) - len(free_candidates)
        if missing <= 0:
            return elements

        source = self._source_element_for_duplicate(candidates)
        for _ in range(missing):
            new_element_id = self._duplicate_element_automatically(
                connection,
                source["epizod_element_id"],
                reason,
            )
            elements = self._episode_elements(connection, episode["epizod_id"])
            candidates = [
                element
                for element in elements
                if str(element.get("klocek_kod") or "").strip().upper()
                in block_codes
            ]
            source = self._source_element_for_duplicate(candidates)
        return elements

    @staticmethod
    def _source_element_for_duplicate(elements):
        return sorted(
            elements,
            key=lambda element: (
                1 if element.get("element_zrodlowy_id") else 0,
                1
                if str(element.get("typ_pochodzenia") or "").upper()
                != "SCIEZKA"
                else 0,
                int(element.get("lp") or 0),
                int(element.get("epizod_element_id") or 0),
            ),
        )[0]

    def _duplicate_element_automatically(
        self,
        connection,
        source_epizod_element_id,
        reason,
    ):
        source = connection.execute(
            """
            SELECT *
            FROM pk_epizod_elementy
            WHERE epizod_element_id = ?
            """,
            (source_epizod_element_id,),
        ).fetchone()
        if source is None:
            raise ValueError("Nie znaleziono elementu źródłowego do powielenia.")

        lp_row = connection.execute(
            """
            SELECT COALESCE(MAX(lp), ?) AS lp
            FROM pk_epizod_elementy
            WHERE epizod_id = ?
              AND klocek_id = ?
            """,
            (
                source["lp"],
                source["epizod_id"],
                source["klocek_id"],
            ),
        ).fetchone()
        desired_lp = int(lp_row["lp"] or source["lp"] or 0) + 1
        completed_row = connection.execute(
            """
            SELECT COALESCE(MAX(ee.lp), 0) AS lp
            FROM pk_epizod_elementy ee
            JOIN pk_zadania z
                ON z.epizod_element_id = ee.epizod_element_id
            WHERE ee.epizod_id = ?
              AND (
                  UPPER(z.status) IN ('ZAKONCZONE', 'ZAKOŃCZONE', 'ZREALIZOWANO', 'ZREALIZOWANE')
                  OR z.data_realizacji IS NOT NULL
              )
            """,
            (source["epizod_id"],),
        ).fetchone()
        new_lp = max(
            desired_lp,
            int(completed_row["lp"] or 0) + 1,
        )
        connection.execute(
            """
            UPDATE pk_epizod_elementy
            SET lp = lp + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE epizod_id = ?
              AND lp >= ?
            """,
            (source["epizod_id"], new_lp),
        )
        cursor = connection.execute(
            """
            INSERT INTO pk_epizod_elementy(
                epizod_id,
                sciezka_element_id,
                klocek_id,
                element_zrodlowy_id,
                nazwa,
                lp,
                min_liczba,
                max_liczba,
                termin_liczba,
                jednostka_czasu_id,
                termin_od_epizod_element_id,
                czy_wymagany,
                czy_wymaga_zlecenia,
                czy_aktywny,
                typ_pochodzenia,
                powod_modyfikacji,
                created_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (
                source["epizod_id"],
                source["sciezka_element_id"],
                source["klocek_id"],
                source_epizod_element_id,
                source["nazwa"],
                new_lp,
                source["min_liczba"],
                source["max_liczba"],
                source["termin_liczba"],
                source["jednostka_czasu_id"],
                source["termin_od_epizod_element_id"],
                source["czy_wymagany"],
                source["czy_wymaga_zlecenia"],
                AUTO_DUPLICATE_ORIGIN,
                reason,
                SYSTEM_USER,
            ),
        )
        new_id = int(cursor.lastrowid)
        after = connection.execute(
            """
            SELECT *
            FROM pk_epizod_elementy
            WHERE epizod_element_id = ?
            """,
            (new_id,),
        ).fetchone()
        record_history(
            connection,
            new_id,
            AUTO_DUPLICATE_ORIGIN,
            after=dict(after) if after is not None else None,
            reason="Dodatkowe zdarzenie pobrane z Eskulap",
            user_id=SYSTEM_USER,
        )
        return new_id

    def _ensure_task(self, connection, episode, element):
        if element.get("zadanie_id"):
            return int(element["zadanie_id"])
        cursor = connection.execute(
            """
            INSERT INTO pk_zadania(
                epizod_id,
                element_id,
                epizod_element_id,
                status,
                zrodlo
            )
            VALUES (?, ?, ?, ?, 'ESKULAP')
            """,
            (
                episode["epizod_id"],
                element.get("element_id"),
                element["epizod_element_id"],
                STATUS_TO_PLAN,
            ),
        )
        return int(cursor.lastrowid)

    def _clear_invalid_specialist_consultation_assignment(self, connection, element):
        if not is_specialist_consultation_block(element.get("klocek_kod")):
            return False
        source = str(element.get("eskulap_system") or "").strip().upper()
        if not source or source == SOURCE_CONSULTATION:
            return False
        task_id = element.get("zadanie_id")
        if not task_id:
            return False

        before = self._task_snapshot(connection, task_id)
        connection.execute(
            """
            UPDATE pk_zadania
            SET data_zaplanowana = NULL,
                data_realizacji = NULL,
                eskulap_system = NULL,
                eskulap_id = NULL,
                eskulap_pracownik = NULL,
                eskulap_data_wizyty = NULL,
                eskulap_rodzaj_wizyty = NULL,
                eskulap_decyzja = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE zadanie_id = ?
            """,
            (task_id,),
        )
        after = self._task_snapshot(connection, task_id)
        record_history(
            connection,
            element["epizod_element_id"],
            "EDYCJA",
            before={"zadanie": before},
            after={"zadanie": after},
            reason=(
                f"{SYNC_REASON} Usunięto błędne powiązanie konsultacji "
                "specjalistycznej z wizytą Eskulap."
            ),
            user_id=SYSTEM_USER,
        )
        element.update(
            {
                "data_zaplanowana": None,
                "data_realizacji": None,
                "eskulap_system": None,
                "eskulap_id": None,
            }
        )
        return True

    def _update_task_from_visit(
        self,
        connection,
        task_id,
        element,
        visit,
    ):
        before = self._task_snapshot(connection, task_id)
        event_date = getattr(visit, "event_date", None) if visit is not None else None
        planned_date = (
            getattr(visit, "planned_date", None)
            if visit is not None
            else None
        )
        source_realization_date = (
            getattr(visit, "realization_date", None)
            if visit is not None
            else None
        )
        visit_name = (
            getattr(visit, "parametr_nazwa", None)
            or getattr(visit, "description", None)
            if visit is not None
            else "Wizyta kwalifikacyjna PKK"
        )
        worker = getattr(visit, "employee_name", None) if visit is not None else None
        oracle_id = getattr(visit, "oracle_id", None) if visit is not None else None
        decision = _decision(visit) if visit is not None else None
        source = _event_source(visit) if visit is not None else SOURCE_SYSTEM
        realization_date = source_realization_date or (
            event_date if decision == "J" else None
        )
        scheduled_date = planned_date or event_date

        changed = (
            not before
            or str(before.get("eskulap_id") or "") != str(oracle_id or "")
            or str(before.get("eskulap_decyzja") or "") != str(decision or "")
            or str(before.get("data_zaplanowana") or "") != str(scheduled_date or "")
            or str(before.get("data_realizacji") or "") != str(realization_date or "")
        )
        if not changed:
            return False
        connection.execute(
            """
            UPDATE pk_zadania
            SET data_zaplanowana = COALESCE(?, data_zaplanowana),
                data_realizacji = COALESCE(?, data_realizacji),
                eskulap_system = COALESCE(?, eskulap_system),
                eskulap_id = COALESCE(?, eskulap_id),
                eskulap_pracownik = COALESCE(?, eskulap_pracownik),
                eskulap_data_wizyty = COALESCE(?, eskulap_data_wizyty),
                eskulap_rodzaj_wizyty = COALESCE(?, eskulap_rodzaj_wizyty),
                eskulap_decyzja = COALESCE(?, eskulap_decyzja),
                uwagi = COALESCE(uwagi, ?),
                updated_at = CURRENT_TIMESTAMP
            WHERE zadanie_id = ?
            """,
            (
                scheduled_date,
                realization_date,
                source,
                str(oracle_id) if oracle_id is not None else None,
                worker,
                event_date or scheduled_date,
                visit_name,
                decision,
                SYNC_REASON,
                task_id,
            ),
        )
        after = self._task_snapshot(connection, task_id)
        record_history(
            connection,
            element["epizod_element_id"],
            "EDYCJA",
            before={"zadanie": before},
            after={"zadanie": after},
            reason=(
                f"{SYNC_REASON} Powiązanie z wizytą Eskulap: "
                f"{oracle_id or 'brak'}; decyzja: {decision or 'brak'}"
            ),
            user_id=SYSTEM_USER,
        )
        return True

    def _task_snapshot(self, connection, task_id):
        row = connection.execute(
            """
            SELECT *
            FROM pk_zadania
            WHERE zadanie_id = ?
            """,
            (task_id,),
        ).fetchone()
        return dict(row) if row is not None else None
