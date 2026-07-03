from dataclasses import dataclass, field
from datetime import date, datetime

from app.repositories.event_repository import (
    EVENT_CONSULTATION,
    EVENT_IMAGING_ORDER,
    EVENT_LABORATORY_ORDER,
    EVENT_VISIT,
    get_patient_consultations,
    get_patient_imaging_orders,
    get_patient_laboratory_orders,
    get_patient_visits,
)
from app.repositories.task_repository import (
    list_active_tasks,
    list_synchronized_event_keys,
)
from episode_generator import complete_task


TASK_EVENT_TYPES = {
    "WIZYTA_PSYCHIATRYCZNA": {EVENT_VISIT},
    "DIAGNOSTYKA_PSYCHOLOGICZNA": {EVENT_VISIT},
    "KONSULTACJA_SPECJALISTYCZNA": {EVENT_CONSULTATION},
    "BADANIE_LAB": {EVENT_LABORATORY_ORDER},
    "BADANIE_GENETYCZNE": {EVENT_LABORATORY_ORDER},
    "BADANIE_OBRAZOWE": {EVENT_IMAGING_ORDER},
}


@dataclass
class SynchronizationResult:
    patients_checked: int = 0
    tasks_checked: int = 0
    tasks_completed: int = 0
    tasks_skipped: int = 0
    errors: list[str] = field(default_factory=list)


def _as_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _event_key(event):
    return str(event.source), str(event.oracle_id)


def _compatible_events(task, events, used_keys):
    event_types = TASK_EVENT_TYPES.get(task["klocek_kod"], set())
    return [
        event
        for event in events
        if event.event_type in event_types
        and _event_key(event) not in used_keys
    ]


def _match_event(task, patient_tasks, events, used_keys):
    candidates = _compatible_events(task, events, used_keys)
    if not candidates:
        return None

    linked_id = str(task.get("eskulap_id") or "").strip()
    linked_system = str(task.get("eskulap_system") or "").strip()
    if linked_id:
        exact = [
            event
            for event in candidates
            if str(event.oracle_id) == linked_id
            and (not linked_system or event.source == linked_system)
        ]
        return exact[0] if len(exact) == 1 else None

    planned_date = _as_date(task.get("data_zaplanowana"))
    if planned_date:
        same_day = [
            event
            for event in candidates
            if _as_date(event.event_date) == planned_date
        ]
        return same_day[0] if len(same_day) == 1 else None

    earliest_date = _as_date(task.get("created_at")) or _as_date(
        task.get("data_start")
    )
    candidates = [
        event
        for event in candidates
        if _as_date(event.event_date)
        and (not earliest_date or _as_date(event.event_date) >= earliest_date)
    ]
    compatible_tasks = [
        other
        for other in patient_tasks
        if TASK_EVENT_TYPES.get(other["klocek_kod"], set())
        & TASK_EVENT_TYPES.get(task["klocek_kod"], set())
    ]
    if len(candidates) == 1 and len(compatible_tasks) == 1:
        return candidates[0]
    return None


def _load_patient_events(patient_id, date_from):
    arguments = (patient_id, date_from, None)
    events = []
    events.extend(get_patient_visits(*arguments))
    events.extend(get_patient_consultations(*arguments))
    events.extend(get_patient_laboratory_orders(*arguments))
    events.extend(get_patient_imaging_orders(*arguments))
    return events


def synchronize_tasks() -> SynchronizationResult:
    result = SynchronizationResult()
    tasks = [
        task
        for task in list_active_tasks()
        if task["klocek_kod"] in TASK_EVENT_TYPES
    ]
    result.tasks_checked = len(tasks)
    used_keys = list_synchronized_event_keys()

    tasks_by_patient = {}
    for task in tasks:
        tasks_by_patient.setdefault(str(task["pacjent_id"]), []).append(task)

    for patient_id, patient_tasks in tasks_by_patient.items():
        result.patients_checked += 1
        start_dates = [
            value
            for value in (
                _as_date(task.get("data_start"))
                for task in patient_tasks
            )
            if value is not None
        ]
        date_from = min(start_dates) if start_dates else None
        try:
            events = _load_patient_events(patient_id, date_from)
        except Exception as exc:
            result.errors.append(f"Pacjent {patient_id}: {exc}")
            result.tasks_skipped += len(patient_tasks)
            continue

        for task in patient_tasks:
            event = _match_event(
                task,
                patient_tasks,
                events,
                used_keys,
            )
            if event is None:
                result.tasks_skipped += 1
                continue
            try:
                complete_task(
                    task["zadanie_id"],
                    data_realizacji=event.event_date,
                    completion_status="ZREALIZOWANO",
                    eskulap_system=event.source,
                    eskulap_id=event.oracle_id,
                )
                used_keys.add(_event_key(event))
                result.tasks_completed += 1
            except Exception as exc:
                result.errors.append(
                    f"Zadanie {task['zadanie_id']}: {exc}"
                )
                result.tasks_skipped += 1

    return result
