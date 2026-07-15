from contextlib import closing

from app.repositories import episode_element_repository as elements
from app.repositories.db_connection import create_connection, initialize_database


EDIT_PERMISSION = "EPISODE_PATH_EDIT"
FULL_EDIT_ROLES = {"ADMIN", "KIEROWNIK"}
LIMITED_EDIT_ROLES = {"KOORDYNATOR"}


def _roles(user):
    if user is None:
        return frozenset()
    return frozenset(str(role).upper() for role in getattr(user, "roles", []))


def _user_id(user):
    return getattr(user, "user_id", user)


def can_edit_episode_path(user) -> bool:
    roles = _roles(user)
    return bool(roles & (FULL_EDIT_ROLES | LIMITED_EDIT_ROLES))


def _require_edit(user):
    if not can_edit_episode_path(user):
        raise PermissionError(
            "Operacja wymaga uprawnienia EPISODE_PATH_EDIT."
        )


def _create_task_for_episode_element(connection, epizod_element_id):
    element = connection.execute(
        """
        SELECT
            epizod_element_id,
            epizod_id,
            sciezka_element_id
        FROM pk_epizod_elementy
        WHERE epizod_element_id = ?
        """,
        (epizod_element_id,),
    ).fetchone()
    if element is None:
        raise ValueError("Nie znaleziono elementu epizodu")
    cursor = connection.execute(
        """
        INSERT INTO pk_zadania(
            epizod_id,
            element_id,
            epizod_element_id,
            status,
            zrodlo
        )
        VALUES (?, ?, ?, 'DO_ZAPLANOWANIA', 'PROGRAM')
        """,
        (
            element["epizod_id"],
            element["sciezka_element_id"],
            element["epizod_element_id"],
        ),
    )
    return int(cursor.lastrowid)


def can_deactivate_element(epizod_element_id):
    return elements.can_deactivate_element(epizod_element_id)


def deactivate_element(epizod_element_id, reason, user):
    _require_edit(user)
    reason = str(reason or "").strip()
    if not reason:
        raise ValueError("Podanie przyczyny dezaktywacji jest wymagane.")
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            elements._deactivate_element(
                connection,
                epizod_element_id,
                reason,
                _user_id(user),
            )


def reactivate_element(
    epizod_element_id,
    reason,
    user,
    create_task=True,
):
    _require_edit(user)
    reason = str(reason or "").strip()
    if not reason:
        raise ValueError("Podanie przyczyny reaktywacji jest wymagane.")
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            elements._reactivate_element(
                connection,
                epizod_element_id,
                reason,
                _user_id(user),
            )
            if create_task:
                _create_task_for_episode_element(
                    connection,
                    epizod_element_id,
                )


def duplicate_element(epizod_element_id, values, reason, user):
    _require_edit(user)
    reason = str(reason or "").strip()
    if not reason:
        raise ValueError("Podanie przyczyny powielenia jest wymagane.")
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            new_id = elements._duplicate_element(
                connection,
                epizod_element_id,
                values or {},
                reason,
                _user_id(user),
            )
            task_id = _create_task_for_episode_element(connection, new_id)
            return {
                "epizod_element_id": new_id,
                "zadanie_id": task_id,
            }


def reorder_episode_elements(epizod_id, ordered_ids, user):
    _require_edit(user)
    return elements.reorder_episode_elements(epizod_id, ordered_ids)


def list_element_dependents(epizod_element_id):
    return elements.list_element_dependents(epizod_element_id)


def list_element_history(epizod_element_id):
    return elements.list_element_history(epizod_element_id)


def can_plan_element(epizod_element_id):
    return elements.can_plan_element(epizod_element_id)


def plan_episode_element(
    epizod_element_id,
    plan_date,
    time_from,
    time_to,
    notes,
    user,
):
    _require_edit(user)
    return elements.plan_episode_element(
        epizod_element_id,
        plan_date,
        time_from,
        time_to,
        notes,
        _user_id(user),
    )


def clear_episode_element_plan(epizod_element_id, user):
    _require_edit(user)
    return elements.clear_episode_element_plan(
        epizod_element_id,
        _user_id(user),
    )
