import re
from contextlib import closing
from datetime import date, datetime

from config import load_config
from db import create_connection


SQL_IDENTIFIER = re.compile(r"^[A-Za-z0-9_$#.]+$")


def _date_text(value, field_name):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value or "").strip()
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError as exc:
        raise ValueError(
            f"Pole {field_name} musi mieć format RRRR-MM-DD"
        ) from exc


def _configured_view_name() -> str:
    config = load_config()
    view_name = str(config.view_name or "").strip()
    if not SQL_IDENTIFIER.fullmatch(view_name):
        raise ValueError("Nieprawidłowa nazwa widoku harmonogramu")
    return view_name


def list_work_schedule(
    jo_id,
    date_from,
    date_to,
    employee_ids=None,
) -> list[dict]:
    """Odczytuje plan pracy z widoku Eskulapa wyłącznie instrukcją SELECT."""

    config = load_config()
    view_name = _configured_view_name()
    parameters = {
        "jo_id": jo_id,
        "date_from": _date_text(date_from, "date_from"),
        "date_to": _date_text(date_to, "date_to"),
    }
    conditions = [
        "p.JO_ID = :jo_id",
        """
        p.DATA_DNIA BETWEEN TO_DATE(:date_from, 'YYYY-MM-DD')
                        AND TO_DATE(:date_to, 'YYYY-MM-DD')
        """,
    ]

    employee_ids = [
        value
        for value in (employee_ids or [])
        if value is not None and str(value).strip()
    ]
    if employee_ids:
        placeholders = []
        for index, employee_id in enumerate(employee_ids):
            name = f"employee_id_{index}"
            placeholders.append(f":{name}")
            parameters[name] = employee_id
        conditions.append(
            "p.PRACOWNIK_ID IN (" + ", ".join(placeholders) + ")"
        )

    sql = f"""
        SELECT
            p.JO_ID,
            p.JO_SYMBOL,
            p.JO_NAZWA,
            p.DATA_DNIA,
            p.DATA_TEKST,
            p.DZIEN_TYG,
            p.PRACOWNIK_ID,
            p.PRACOWNIK,
            p.GODZ_OD,
            p.GODZ_DO,
            p.PLN_ID,
            p.PLN_OPIS,
            p.RODZAJE_WIZYT_KODY
        FROM {view_name} p
        WHERE {" AND ".join(conditions)}
        ORDER BY p.DATA_DNIA, p.GODZ_OD, p.PRACOWNIK
    """
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
            return [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]


__all__ = ["list_work_schedule"]
