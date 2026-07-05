from contextlib import closing
from datetime import date, datetime, timedelta

from config import load_config
from db import create_connection
from episode_generator import create_episode_with_tasks
from app.repositories.db_connection import (
    create_connection as create_local_connection,
    initialize_database as initialize_local_db,
    is_integrity_error,
)
from app.repositories.patient_repository import PATIENTS_VIEW, VISITS_VIEW


SOURCE_SYSTEM = "ESKULAP"
SOURCE_TYPE = "WIZYTA_KWALIFIKACYJNA_PKK"
# F18 = rodzaj wizyty kwalifikacyjnej PKK w Eskulapie.
QUALIFICATION_VISIT_TYPE = "F18"


def _date_value(value, field_name):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError as exc:
        raise ValueError(
            f"Pole {field_name} musi mieć format RRRR-MM-DD"
        ) from exc


def _oracle_query(sql, parameters=None, fetch_one=False):
    config = load_config()
    with closing(
        create_connection(
            config.database_user,
            config.database_password,
            config.database_dsn,
        )
    ) as connection:
        with closing(connection.cursor()) as cursor:
            cursor.execute(sql, parameters or {})
            columns = [column[0].lower() for column in cursor.description]
            if fetch_one:
                row = cursor.fetchone()
                return dict(zip(columns, row)) if row is not None else None
            return [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]


def _episode_assignments() -> dict[str, int]:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        rows = connection.execute(
            """
            SELECT source_id, epizod_id
            FROM pk_epizody
            WHERE source_system = ?
              AND source_type = ?
              AND source_id IS NOT NULL
            """,
            (SOURCE_SYSTEM, SOURCE_TYPE),
        ).fetchall()
    return {
        str(row["source_id"]): int(row["epizod_id"])
        for row in rows
    }


def _with_assignment(visit, assignments):
    if visit is None:
        return None
    result = dict(visit)
    episode_id = assignments.get(str(result["wizyta_id"]))
    result["epizod_id"] = episode_id
    result["assignment_status"] = (
        "PRZYPISANA" if episode_id is not None else "NIEPRZYPISANA"
    )
    return result


def _qualification_condition(alias="w"):
    return f"""
        UPPER(TRIM(NVL({alias}.TYP_WIZYTY, ''))) =
            UPPER(:qualification_visit_type)
    """


def _qualification_parameters():
    return {
        "qualification_visit_type": QUALIFICATION_VISIT_TYPE,
    }


def list_qualification_visits(
    date_from=None,
    date_to=None,
    only_unassigned=True,
) -> list[dict]:
    date_from = _date_value(date_from, "date_from")
    date_to = _date_value(date_to, "date_to")
    if date_from and date_to and date_from > date_to:
        raise ValueError("date_from nie może być późniejsza niż date_to")

    conditions = [_qualification_condition("w")]
    parameters = _qualification_parameters()
    if date_from:
        conditions.append("w.DATA_WIZYTY >= :date_from")
        parameters["date_from"] = date_from
    if date_to:
        conditions.append("w.DATA_WIZYTY < :date_to_exclusive")
        parameters["date_to_exclusive"] = date_to + timedelta(days=1)
    where_clause = "WHERE " + " AND ".join(conditions)

    visits = _oracle_query(
        f"""
        SELECT
            w.*,
            p.PESEL,
            p.NAZWISKO,
            p.IMIE,
            w.PORADNIA_NAZWA AS PORADNIA,
            w.DECYZJA AS STATUS_WIZYTY
        FROM {VISITS_VIEW} w
        LEFT JOIN {PATIENTS_VIEW} p
            ON p.PACJENT_ID = w.PACJENT_ID
        {where_clause}
        ORDER BY w.DATA_WIZYTY DESC, w.WIZYTA_ID DESC
        """,
        parameters,
    )
    assignments = _episode_assignments()
    result = [_with_assignment(visit, assignments) for visit in visits]
    if only_unassigned:
        result = [
            visit
            for visit in result
            if visit["epizod_id"] is None
        ]
    return result


def get_qualification_visit(wizyta_id):
    parameters = _qualification_parameters()
    parameters["wizyta_id"] = wizyta_id
    visit = _oracle_query(
        f"""
        SELECT
            w.*,
            p.PESEL,
            p.NAZWISKO,
            p.IMIE,
            w.PORADNIA_NAZWA AS PORADNIA,
            w.DECYZJA AS STATUS_WIZYTY
        FROM {VISITS_VIEW} w
        LEFT JOIN {PATIENTS_VIEW} p
            ON p.PACJENT_ID = w.PACJENT_ID
        WHERE w.WIZYTA_ID = :wizyta_id
          AND {_qualification_condition("w")}
          AND ROWNUM = 1
        """,
        parameters,
        fetch_one=True,
    )
    return _with_assignment(visit, _episode_assignments())


def _episode_start_date(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value or "").strip()
    if len(text) < 10:
        raise ValueError("Wizyta kwalifikacyjna nie ma poprawnej daty")
    return text[:10]


def create_episode_from_qualification_visit(
    wizyta_id,
    program_id,
    sciezka_id,
    koordynator_id=None,
) -> int:
    visit = get_qualification_visit(wizyta_id)
    if visit is None:
        raise ValueError("Nie znaleziono wizyty kwalifikacyjnej w Eskulapie")
    if visit["epizod_id"] is not None:
        raise ValueError(
            f"Wizyta jest już przypisana do epizodu {visit['epizod_id']}"
        )
    if visit.get("pacjent_id") is None:
        raise ValueError("Wizyta nie zawiera identyfikatora pacjenta")

    try:
        return create_episode_with_tasks(
            pacjent_id=str(visit["pacjent_id"]),
            program_id=program_id,
            sciezka_id=sciezka_id,
            data_start=_episode_start_date(visit.get("data_wizyty")),
            koordynator_id=koordynator_id,
            source_system=SOURCE_SYSTEM,
            source_type=SOURCE_TYPE,
            source_id=str(wizyta_id),
        )
    except Exception as exc:
        if not is_integrity_error(exc):
            raise
        raise ValueError(
            "Wizyta kwalifikacyjna została już przypisana do epizodu"
        ) from exc
