from collections import defaultdict
from contextlib import closing
from datetime import date, datetime

from app.repositories.db_connection import (
    create_connection as create_local_connection,
    initialize_database as initialize_local_db,
    patient_id_column,
)


FILTER_ACTIVE = "DASHBOARD_ACTIVE"
FILTER_TO_PLAN = "DASHBOARD_TO_PLAN"
FILTER_OVERDUE = "DASHBOARD_OVERDUE"
FILTER_SCHEDULED_TODAY = "DASHBOARD_SCHEDULED_TODAY"
FILTER_WAITING_ESKULAP = "DASHBOARD_WAITING_ESKULAP"
FILTER_COMPLETED_MONTH = "DASHBOARD_COMPLETED_MONTH"

COMPLETED_TASK_STATUSES = {
    "ZAKONCZONE",
    "ZAKOŃCZONE",
    "ZREALIZOWANO",
    "ZREALIZOWANE",
}
CANCELLED_TASK_STATUSES = {
    "ANULOWANE",
    "ANULOWANO",
}
TERMINAL_TASK_STATUSES = COMPLETED_TASK_STATUSES | CANCELLED_TASK_STATUSES
TERMINAL_EPISODE_STATUSES = {
    "ZAKONCZONY",
    "ZAKOŃCZONY",
    "ZAKONCZONE",
    "ZAKOŃCZONE",
    "ANULOWANY",
    "ANULOWANE",
}
WAITING_ESKULAP_STATUSES = {
    "OCZEKUJE NA ESKULAP",
    "OCZEKUJE NA DANE Z ESKULAPA",
    "OCZEKUJE_NA_ESKULAP",
    "OCZEKUJE_NA_DANE_Z_ESKULAPA",
}


def _normalized_status(value):
    return str(value or "").strip().upper()


def _date_value(value):
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


def _unit_id(unit):
    if unit is None:
        return None
    if isinstance(unit, dict):
        value = unit.get("jo_id")
    else:
        value = getattr(unit, "jo_id", unit)
    text = str(value or "").strip()
    return text or None


def _is_admin(user):
    return bool(user is not None and getattr(user, "is_admin", False))


def _user_id(user):
    value = getattr(user, "user_id", None) if user is not None else None
    return value


def _load_unit_maps(connection):
    program_units = defaultdict(list)
    pathway_units = defaultdict(list)
    for table, key, target in (
        ("pk_program_units", "program_id", program_units),
        ("pk_pathway_units", "sciezka_id", pathway_units),
    ):
        rows = connection.execute(
            f"""
            SELECT {key}, jo_id, jo_symbol, jo_nazwa
            FROM {table}
            ORDER BY jo_symbol COLLATE NOCASE, jo_nazwa COLLATE NOCASE, jo_id
            """
        ).fetchall()
        for row in rows:
            target[row[key]].append(
                {
                    "jo_id": str(row["jo_id"]),
                    "jo_symbol": row["jo_symbol"],
                    "jo_nazwa": row["jo_nazwa"],
                }
            )
    return program_units, pathway_units


def _allowed_unit_ids(connection, current_user, current_unit):
    selected_unit = _unit_id(current_unit)
    if selected_unit:
        return {selected_unit}
    if current_user is None or _is_admin(current_user):
        return None
    user_id = _user_id(current_user)
    if user_id is None:
        return set()
    rows = connection.execute(
        """
        SELECT jo_id
        FROM pk_user_units
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchall()
    return {str(row["jo_id"]) for row in rows}


def _episode_units(episode, program_units, pathway_units):
    units = pathway_units.get(episode["sciezka_id"])
    if not units:
        units = program_units.get(episode["program_id"], [])
    return list(units)


def _load_dashboard_episodes(current_user=None, current_unit=None):
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        episodes = [
            dict(row)
            for row in connection.execute(
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
        ]
        tasks = [
            dict(row)
            for row in connection.execute(
                """
                SELECT
                    z.zadanie_id,
                    z.epizod_id,
                    z.element_id,
                    z.status,
                    z.data_wymagana_do,
                    z.data_zaplanowana,
                    z.data_realizacji,
                    z.eskulap_system,
                    z.eskulap_id,
                    el.lp,
                    el.nazwa_w_sciezce,
                    el.czy_wymaga_zlecenia,
                    el.czy_aktywny,
                    k.nazwa AS klocek_nazwa
                FROM pk_zadania z
                LEFT JOIN pk_sciezka_elementy el
                    ON el.element_id = z.element_id
                LEFT JOIN pk_klocki k ON k.klocek_id = el.klocek_id
                ORDER BY z.epizod_id, el.lp, z.zadanie_id
                """
            ).fetchall()
        ]
        program_units, pathway_units = _load_unit_maps(connection)
        allowed_units = _allowed_unit_ids(
            connection,
            current_user,
            current_unit,
        )

    tasks_by_episode = defaultdict(list)
    for task in tasks:
        if task["czy_aktywny"] in (None, 1, True):
            tasks_by_episode[task["epizod_id"]].append(task)

    today = date.today()
    month_start = today.replace(day=1)
    result = []
    for episode in episodes:
        units = _episode_units(episode, program_units, pathway_units)
        unit_ids = [unit["jo_id"] for unit in units]
        if allowed_units is not None and not (
            set(unit_ids) & allowed_units
        ):
            continue

        episode_tasks = tasks_by_episode.get(episode["epizod_id"], [])
        progress_tasks = [
            task
            for task in episode_tasks
            if _normalized_status(task["status"])
            not in CANCELLED_TASK_STATUSES
        ]
        completed_count = sum(
            _normalized_status(task["status"])
            in COMPLETED_TASK_STATUSES
            for task in progress_tasks
        )
        total_count = len(progress_tasks)
        progress = (
            round(100.0 * completed_count / total_count, 1)
            if total_count
            else 0.0
        )

        open_tasks = [
            task
            for task in episode_tasks
            if _normalized_status(task["status"])
            not in TERMINAL_TASK_STATUSES
        ]
        for task in open_tasks:
            task["termin"] = (
                task["data_zaplanowana"]
                or task["data_wymagana_do"]
            )
        next_task = min(
            open_tasks,
            key=lambda task: (
                _date_value(task["termin"]) is None,
                _date_value(task["termin"]) or date.max,
                task["lp"] if task["lp"] is not None else 999999,
                task["zadanie_id"],
            ),
            default=None,
        )

        has_to_plan = any(
            _normalized_status(task["status"]) == "DO_ZAPLANOWANIA"
            for task in open_tasks
        )
        has_overdue = any(
            _date_value(task["termin"]) is not None
            and _date_value(task["termin"]) < today
            for task in open_tasks
        )
        scheduled_today_count = sum(
            _date_value(task["data_zaplanowana"]) == today
            for task in open_tasks
        )
        has_scheduled_today = scheduled_today_count > 0
        waiting_for_eskulap = any(
            _normalized_status(task["status"])
            in WAITING_ESKULAP_STATUSES
            or (
                bool(task["czy_wymaga_zlecenia"])
                and not task["eskulap_id"]
                and _normalized_status(task["status"])
                == "DO_ZAPLANOWANIA"
            )
            for task in open_tasks
        )
        end_date = _date_value(episode["data_zakonczenia"])
        completed_this_month = bool(
            end_date
            and month_start <= end_date <= today
        )
        is_active = (
            end_date is None
            and _normalized_status(episode["status"])
            not in TERMINAL_EPISODE_STATUSES
        )

        row = dict(episode)
        row.update(
            {
                "liczba_zadan": total_count,
                "liczba_zrealizowanych_zadan": completed_count,
                "procent_realizacji": progress,
                "next_task_id": (
                    next_task["zadanie_id"] if next_task else None
                ),
                "next_task_name": (
                    (
                        next_task["nazwa_w_sciezce"]
                        or next_task["klocek_nazwa"]
                    )
                    if next_task
                    else None
                ),
                "next_task_due": (
                    next_task["termin"] if next_task else None
                ),
                "next_task_status": (
                    next_task["status"] if next_task else None
                ),
                "unit_ids": unit_ids,
                "unit_symbols": [
                    unit["jo_symbol"] or unit["jo_id"]
                    for unit in units
                ],
                "unit_names": [
                    unit["jo_nazwa"] or unit["jo_symbol"] or unit["jo_id"]
                    for unit in units
                ],
                "is_active": is_active,
                "has_to_plan": has_to_plan,
                "has_overdue": has_overdue,
                "has_scheduled_today": has_scheduled_today,
                "scheduled_today_count": scheduled_today_count,
                "waiting_for_eskulap": waiting_for_eskulap,
                "completed_this_month": completed_this_month,
            }
        )
        result.append(row)
    return result


def _matches_status_filter(episode, status_filter):
    if not status_filter:
        return True
    special_filters = {
        FILTER_ACTIVE: "is_active",
        FILTER_TO_PLAN: "has_to_plan",
        FILTER_OVERDUE: "has_overdue",
        FILTER_SCHEDULED_TODAY: "has_scheduled_today",
        FILTER_WAITING_ESKULAP: "waiting_for_eskulap",
        FILTER_COMPLETED_MONTH: "completed_this_month",
    }
    flag = special_filters.get(status_filter)
    if flag:
        return bool(episode[flag])
    return _normalized_status(episode["status"]) == _normalized_status(
        status_filter
    )


def list_dashboard_episodes(
    current_user=None,
    current_unit=None,
    status_filter=None,
):
    return [
        episode
        for episode in _load_dashboard_episodes(
            current_user,
            current_unit,
        )
        if _matches_status_filter(episode, status_filter)
    ]


def get_dashboard_summary(current_user=None, current_unit=None):
    episodes = _load_dashboard_episodes(current_user, current_unit)
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


def get_episode_progress(epizod_id):
    episode = next(
        (
            row
            for row in _load_dashboard_episodes()
            if int(row["epizod_id"]) == int(epizod_id)
        ),
        None,
    )
    if episode is None:
        raise ValueError(f"Nie znaleziono epizodu o ID {epizod_id}")
    return {
        "epizod_id": episode["epizod_id"],
        "liczba_zadan": episode["liczba_zadan"],
        "liczba_zrealizowanych_zadan": (
            episode["liczba_zrealizowanych_zadan"]
        ),
        "procent_realizacji": episode["procent_realizacji"],
    }


def get_next_task(epizod_id):
    episode = next(
        (
            row
            for row in _load_dashboard_episodes()
            if int(row["epizod_id"]) == int(epizod_id)
        ),
        None,
    )
    if episode is None:
        raise ValueError(f"Nie znaleziono epizodu o ID {epizod_id}")
    if episode["next_task_id"] is None:
        return None
    return {
        "zadanie_id": episode["next_task_id"],
        "nazwa": episode["next_task_name"],
        "termin": episode["next_task_due"],
        "status": episode["next_task_status"],
    }
