from contextlib import closing
from datetime import date, datetime, timedelta

from config import load_config
from db import create_connection


PATIENTS_VIEW = "ESK_RAPORTY.V_KOMPAS_PACJENCI"
VISITS_VIEW = "ESK_RAPORTY.V_KOMPAS_WIZYTY"
CONSULTATIONS_VIEW = "ESK_RAPORTY.V_KOMPAS_KONSULTACJE"
EXAMS_VIEW = "ESK_RAPORTY.V_KOMPAS_BADANIA"
MAX_SEARCH_LIMIT = 500


def _required_text(value, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"Pole {field_name} jest wymagane")
    return text


def _date_value(value, field_name: str):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise ValueError(
            f"Pole {field_name} musi mieć format RRRR-MM-DD"
        ) from exc


def _query(sql: str, parameters=None, fetch_one=False):
    config = load_config()
    parameters = parameters or {}
    with closing(
        create_connection(
            config.database_user,
            config.database_password,
            config.database_dsn,
        )
    ) as connection:
        with closing(connection.cursor()) as cursor:
            cursor.execute(sql, parameters)
            columns = [column[0].lower() for column in cursor.description]
            if fetch_one:
                row = cursor.fetchone()
                return dict(zip(columns, row)) if row is not None else None
            return [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]


def search_patients(search_text, limit=50) -> list[dict]:
    search_text = _required_text(search_text, "search_text")
    row_limit = int(limit)
    if row_limit < 1 or row_limit > MAX_SEARCH_LIMIT:
        raise ValueError(
            f"Pole limit musi mieścić się w zakresie 1-{MAX_SEARCH_LIMIT}"
        )

    return _query(
        f"""
        SELECT *
        FROM (
            SELECT p.*
            FROM {PATIENTS_VIEW} p
            WHERE UPPER(p.NAZWISKO) LIKE UPPER(:search_pattern)
               OR p.PESEL LIKE :search_pattern
            ORDER BY p.NAZWISKO, p.IMIE, p.PACJENT_ID
        )
        WHERE ROWNUM <= :row_limit
        """,
        {
            "search_pattern": f"%{search_text}%",
            "row_limit": row_limit,
        },
    )


def get_patient(pacjent_id):
    pacjent_id = _required_text(pacjent_id, "pacjent_id")
    return _query(
        f"""
        SELECT p.*
        FROM {PATIENTS_VIEW} p
        WHERE p.PACJENT_ID = :pacjent_id
          AND ROWNUM = 1
        """,
        {"pacjent_id": pacjent_id},
        fetch_one=True,
    )


def get_patient_visits(
    pacjent_id,
    date_from=None,
    date_to=None,
) -> list[dict]:
    pacjent_id = _required_text(pacjent_id, "pacjent_id")
    date_from = _date_value(date_from, "date_from")
    date_to = _date_value(date_to, "date_to")
    if date_from and date_to and date_from > date_to:
        raise ValueError("date_from nie może być późniejsza niż date_to")

    conditions = ["w.PACJENT_ID = :pacjent_id"]
    parameters = {"pacjent_id": pacjent_id}
    if date_from:
        conditions.append("w.DATA_WIZYTY >= :date_from")
        parameters["date_from"] = date_from
    if date_to:
        conditions.append("w.DATA_WIZYTY < :date_to_exclusive")
        parameters["date_to_exclusive"] = date_to + timedelta(days=1)

    return _query(
        f"""
        SELECT w.*
        FROM {VISITS_VIEW} w
        WHERE {" AND ".join(conditions)}
        ORDER BY w.DATA_WIZYTY DESC
        """,
        parameters,
    )


def get_patient_consultations(
    pacjent_id,
    date_from=None,
    date_to=None,
) -> list[dict]:
    pacjent_id = _required_text(pacjent_id, "pacjent_id")
    date_from = _date_value(date_from, "date_from")
    date_to = _date_value(date_to, "date_to")
    if date_from and date_to and date_from > date_to:
        raise ValueError("date_from nie może być późniejsza niż date_to")

    conditions = ["k.PACJENT_ID = :pacjent_id"]
    parameters = {"pacjent_id": pacjent_id}
    if date_from:
        conditions.append("k.DATA_KONSULTACJI >= :date_from")
        parameters["date_from"] = date_from
    if date_to:
        conditions.append("k.DATA_KONSULTACJI < :date_to_exclusive")
        parameters["date_to_exclusive"] = date_to + timedelta(days=1)

    return _query(
        f"""
        SELECT k.*
        FROM {CONSULTATIONS_VIEW} k
        WHERE {" AND ".join(conditions)}
        ORDER BY k.DATA_KONSULTACJI DESC
        """,
        parameters,
    )


def get_patient_exams(
    pacjent_id,
    date_from=None,
    date_to=None,
) -> list[dict]:
    pacjent_id = _required_text(pacjent_id, "pacjent_id")
    date_from = _date_value(date_from, "date_from")
    date_to = _date_value(date_to, "date_to")
    if date_from and date_to and date_from > date_to:
        raise ValueError("date_from nie może być późniejsza niż date_to")

    conditions = ["b.PACJENT_ID = :pacjent_id"]
    parameters = {"pacjent_id": pacjent_id}
    if date_from:
        conditions.append("b.DATA_SKIEROWANIA >= :date_from")
        parameters["date_from"] = date_from
    if date_to:
        conditions.append("b.DATA_SKIEROWANIA < :date_to_exclusive")
        parameters["date_to_exclusive"] = date_to + timedelta(days=1)

    return _query(
        f"""
        SELECT b.*
        FROM {EXAMS_VIEW} b
        WHERE {" AND ".join(conditions)}
        ORDER BY b.DATA_SKIEROWANIA DESC
        """,
        parameters,
    )
