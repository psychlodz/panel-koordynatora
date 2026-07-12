from __future__ import annotations

from datetime import date, datetime


WAITING_STATUS = "OCZEKUJE NA AKTYWACJĘ"


def _is_empty(value):
    return value is None or str(value).strip() == ""


def text_or_missing(value):
    return "brak" if _is_empty(value) else str(value).strip()


def _format_date(value):
    if _is_empty(value):
        return "brak"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()[:10] or "brak"


def _format_datetime(value):
    if _is_empty(value):
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, date):
        return value.isoformat()
    value = str(value).strip()
    return value[:16] if len(value) >= 16 else value


def process_element_label(record):
    name = (
        record.get("nazwa_w_sciezce")
        or record.get("klocek_nazwa")
        or "Element procesu"
    )
    suffix = ""
    if not record.get("czy_aktywny", 1):
        suffix = " [Dezaktywowany]"
    elif record.get("typ_pochodzenia") == "POWIELENIE":
        suffix = " [Powielenie]"
    deadline = _format_date(record.get("data_wymagana_do"))
    return f"{name}{suffix}\nData realizacji do: {deadline}"


def status_with_date(record):
    status = record.get("status") or WAITING_STATUS
    status_upper = str(status).strip().upper()
    date_value = record.get("status_data_czas")
    if status_upper == "ZAPLANOWANA":
        date_value = date_value or record.get("data_zaplanowana")
    elif status_upper == "ZREALIZOWANA":
        date_value = date_value or record.get("data_realizacji")
    elif status_upper == "ANULOWANA":
        date_value = date_value or (
            record.get("eskulap_data_wizyty")
            or record.get("data_realizacji")
            or record.get("data_zaplanowana")
        )
    formatted = _format_datetime(date_value)
    return f"{status}\n{formatted}" if formatted else str(status)


def eskulap_visit_details(record):
    worker = text_or_missing(record.get("eskulap_pracownik"))
    visit_type = text_or_missing(record.get("eskulap_rodzaj_wizyty"))
    if worker == "brak" and visit_type == "brak":
        return "brak"
    if worker == "brak":
        return visit_type
    if visit_type == "brak":
        return worker
    return f"{worker}\n{visit_type}"
