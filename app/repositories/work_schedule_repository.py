import re
from contextlib import closing
from datetime import date, datetime
import logging

from config import load_config
from db import create_connection


SQL_IDENTIFIER = re.compile(r"^[A-Za-z0-9_$#.]+$")
logger = logging.getLogger(__name__)


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


def _is_missing_visit_types_column_error(error) -> bool:
    parts = [str(error)]
    for arg in getattr(error, "args", ()) or ():
        parts.append(str(arg))
        for attribute in ("code", "message", "full_code"):
            value = getattr(arg, attribute, None)
            if value is not None:
                parts.append(str(value))
    text = " ".join(parts).upper()
    return (
        "ORA-00904" in text
        and "RODZAJE_WIZYT_KODY" in text
    )


def _split_oracle_object_name(view_name):
    parts = [part.strip('"').upper() for part in view_name.split(".")]
    if len(parts) == 2:
        return parts[0], parts[1]
    return None, parts[0]


def _view_has_column(cursor, view_name, column_name):
    owner, object_name = _split_oracle_object_name(view_name)
    parameters = {
        "table_name": object_name,
        "column_name": column_name.upper(),
    }
    owner_condition = ""
    if owner:
        owner_condition = "AND owner = :owner"
        parameters["owner"] = owner
    cursor.execute(
        f"""
        SELECT 1
        FROM all_tab_columns
        WHERE table_name = :table_name
          AND column_name = :column_name
          {owner_condition}
          AND ROWNUM = 1
        """,
        parameters,
    )
    return cursor.fetchone() is not None


def _work_schedule_sql(view_name, conditions, include_visit_types=True):
    visit_types_expression = (
        "p.RODZAJE_WIZYT_KODY"
        if include_visit_types
        else "CAST(NULL AS VARCHAR2(4000)) AS RODZAJE_WIZYT_KODY"
    )
    return f"""
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
            {visit_types_expression}
        FROM {view_name} p
        WHERE {" AND ".join(conditions)}
        ORDER BY p.DATA_DNIA, p.GODZ_OD, p.PRACOWNIK
    """


def _fetch_schedule_rows(cursor, sql, parameters):
    cursor.execute(sql, parameters)
    columns = [column[0].lower() for column in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


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

    with closing(
        create_connection(
            config.database_user,
            config.database_password,
            config.database_dsn,
        )
    ) as connection:
        with closing(connection.cursor()) as cursor:
            try:
                include_visit_types = _view_has_column(
                    cursor,
                    view_name,
                    "RODZAJE_WIZYT_KODY",
                )
            except Exception:
                logger.exception(
                    "Nie udało się sprawdzić metadanych widoku %s. "
                    "Próba pobrania harmonogramu z RODZAJE_WIZYT_KODY.",
                    view_name,
                )
                include_visit_types = True
            if not include_visit_types:
                logger.warning(
                    "Widok harmonogramu %s nie zawiera kolumny "
                    "RODZAJE_WIZYT_KODY. Harmonogram zostanie pobrany bez "
                    "dekodowania rodzajów wizyt.",
                    view_name,
                )
            sql = _work_schedule_sql(
                view_name,
                conditions,
                include_visit_types=include_visit_types,
            )
            try:
                return _fetch_schedule_rows(cursor, sql, parameters)
            except Exception as exc:
                if not _is_missing_visit_types_column_error(exc):
                    raise
                logger.warning(
                    "Widok harmonogramu %s nie zawiera kolumny "
                    "RODZAJE_WIZYT_KODY. Harmonogram zostanie pobrany bez "
                    "dekodowania rodzajów wizyt. Odtwórz widok Oracle z "
                    "docs/SQL/kompas_oracle_views.sql.",
                    view_name,
                )
                fallback_sql = _work_schedule_sql(
                    view_name,
                    conditions,
                    include_visit_types=False,
                )
                return _fetch_schedule_rows(cursor, fallback_sql, parameters)


__all__ = ["list_work_schedule"]
