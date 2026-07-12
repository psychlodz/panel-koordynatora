from collections import defaultdict
from contextlib import closing

from app.repositories.db_connection import create_connection, initialize_database
from app.services.episode_state_service import (
    EpisodeStateService,
    normalized_status,
)


FILTER_ACTIVE = "DASHBOARD_ACTIVE"
FILTER_TO_PLAN = "DASHBOARD_TO_PLAN"
FILTER_OVERDUE = "DASHBOARD_OVERDUE"
FILTER_SCHEDULED_TODAY = "DASHBOARD_SCHEDULED_TODAY"
FILTER_WAITING_ESKULAP = "DASHBOARD_WAITING_ESKULAP"
FILTER_COMPLETED_MONTH = "DASHBOARD_COMPLETED_MONTH"


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
    return getattr(user, "user_id", None) if user is not None else None


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
    initialize_database()
    with closing(create_connection()) as connection:
        program_units, pathway_units = _load_unit_maps(connection)
        allowed_units = _allowed_unit_ids(
            connection,
            current_user,
            current_unit,
        )

    episodes = EpisodeStateService().calculate_all_episode_states()
    visible = []
    for episode in episodes:
        units = _episode_units(episode, program_units, pathway_units)
        unit_ids = [unit["jo_id"] for unit in units]
        if allowed_units is not None and not (
            set(unit_ids) & allowed_units
        ):
            continue

        row = dict(episode)
        row.update(
            {
                "unit_ids": unit_ids,
                "unit_symbols": [
                    unit["jo_symbol"] or unit["jo_id"]
                    for unit in units
                ],
                "unit_names": [
                    unit["jo_nazwa"] or unit["jo_symbol"] or unit["jo_id"]
                    for unit in units
                ],
            }
        )
        visible.append(row)
    return visible


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
    return normalized_status(episode["status"]) == normalized_status(
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
    return EpisodeStateService().calculate_dashboard_counters(episodes)


def get_episode_progress(epizod_id):
    return EpisodeStateService().calculate_progress(epizod_id)


def get_next_task(epizod_id):
    next_task = EpisodeStateService().calculate_next_task(epizod_id)
    if next_task is None:
        return None
    return {
        "zadanie_id": next_task["zadanie_id"],
        "nazwa": next_task["nazwa_w_sciezce"] or next_task["klocek_nazwa"],
        "termin": next_task["termin"],
        "status": next_task["status_wyliczony"],
    }
