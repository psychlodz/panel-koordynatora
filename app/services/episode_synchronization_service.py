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
PKK_KWAL_BLOCK_CODE = "PKK_KWAL"

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
    return SOURCE_SYSTEM, str(getattr(visit, "oracle_id", "") or "")


def _decision(visit):
    return str(getattr(visit, "status", "") or "").strip().upper()


def mapped_block_code(visit, visit_mapping):
    code = str(getattr(visit, "parametr_kod", "") or "").strip().upper()
    return visit_mapping.get(code)


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
        if not block_code or block_code == PKK_KWAL_BLOCK_CODE:
            continue
        free_elements_by_block.setdefault(block_code, []).append(element)

    assignments = []
    used_visit_keys = set(used_visit_keys or set())
    sorted_visits = sorted(
        visits,
        key=lambda visit: (
            _as_datetime(getattr(visit, "event_date", None)) or datetime.max,
            str(getattr(visit, "oracle_id", "") or ""),
        ),
    )
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
                        summary.visits += len(visits)
                        result = self._synchronize_episode(
                            connection,
                            episode,
                            visits,
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
                    summary.visits = len(visits)
                    result = self._synchronize_episode(
                        connection,
                        episode,
                        visits,
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
            keys.add((SOURCE_SYSTEM, oracle_id))
        return keys

    def _episode_elements(self, connection, epizod_id):
        rows = connection.execute(
            """
            SELECT
                ee.epizod_element_id,
                ee.epizod_id,
                ee.sciezka_element_id AS element_id,
                ee.lp,
                ee.nazwa,
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
        return result

    def _qualification_visit(self, episode, visits):
        source_id = str(episode.get("source_id") or "")
        if source_id:
            for visit in visits:
                if str(getattr(visit, "oracle_id", "") or "") == source_id:
                    return visit
        return None

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

    def _update_task_from_visit(
        self,
        connection,
        task_id,
        element,
        visit,
    ):
        before = self._task_snapshot(connection, task_id)
        event_date = getattr(visit, "event_date", None) if visit is not None else None
        visit_name = (
            getattr(visit, "parametr_nazwa", None)
            if visit is not None
            else "Wizyta kwalifikacyjna PKK"
        )
        worker = getattr(visit, "employee_name", None) if visit is not None else None
        oracle_id = getattr(visit, "oracle_id", None) if visit is not None else None
        decision = _decision(visit) if visit is not None else None
        source = SOURCE_SYSTEM

        changed = (
            not before
            or str(before.get("eskulap_id") or "") != str(oracle_id or "")
            or str(before.get("eskulap_decyzja") or "") != str(decision or "")
        )
        if not changed:
            return False
        connection.execute(
            """
            UPDATE pk_zadania
            SET data_realizacji = COALESCE(?, data_realizacji),
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
                event_date,
                source,
                str(oracle_id) if oracle_id is not None else None,
                worker,
                event_date,
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
