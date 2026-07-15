from __future__ import annotations

from datetime import date, datetime


WAITING_STATUS = "OCZEKUJE NA AKTYWACJĘ"
AUTO_DUPLICATE_ORIGIN = "POWIELENIE_AUTOMATYCZNE"
SOURCE_CONSULTATION = "ESKULAP_KONSULTACJE"
SOURCE_IMAGING = "ESKULAP_BADANIA_OBRAZOWE"
MANUAL_PLANNING_BLOCKS = {"KONSULTACJA_SPECJALISTYCZNA", "BADANIE_OBRAZOWE"}


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


def _uses_manual_kompas_planning(record):
    block_code = str(record.get("klocek_kod") or "").strip().upper()
    source = str(record.get("eskulap_system") or "").strip().upper()
    return block_code in MANUAL_PLANNING_BLOCKS or source in {
        SOURCE_CONSULTATION,
        SOURCE_IMAGING,
    }


def process_element_label(record):
    name = (
        record.get("nazwa_w_sciezce")
        or record.get("klocek_nazwa")
        or "Element procesu"
    )
    suffix = ""
    if not record.get("czy_aktywny", 1):
        suffix = " [Dezaktywowany]"
    elif record.get("typ_pochodzenia") == AUTO_DUPLICATE_ORIGIN:
        suffix = " [Powielenie z Eskulap]"
    elif record.get("typ_pochodzenia") == "POWIELENIE":
        suffix = " [Powielenie]"
    deadline = _format_date(record.get("data_wymagana_do"))
    return f"{name}{suffix}\nData realizacji do: {deadline}"


def process_element_tooltip(record):
    tooltip = process_element_label(record)
    if record.get("typ_pochodzenia") == AUTO_DUPLICATE_ORIGIN:
        details = [
            "",
            "Powielenie z Eskulap",
            "Element został utworzony automatycznie podczas synchronizacji,",
            "ponieważ w Eskulapie znaleziono dodatkowe zdarzenie dla tego typu klocka.",
        ]
        source_element_id = record.get("element_zrodlowy_id")
        if source_element_id:
            details.append(f"Element źródłowy: {source_element_id}")
        eskulap_system = record.get("eskulap_system")
        eskulap_id = record.get("eskulap_id")
        if eskulap_system or eskulap_id:
            details.append(
                f"Zdarzenie Eskulap: {text_or_missing(eskulap_system)} / "
                f"{text_or_missing(eskulap_id)}"
            )
        tooltip = "\n".join([tooltip, *details])
    return tooltip


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
    if _uses_manual_kompas_planning(record):
        planned = _format_datetime(record.get("eskulap_plan_data"))
        lines = []
        if visit_type != "brak":
            lines.append(visit_type)
        if planned:
            lines.append(f"Data planowana w Eskulapie: {planned}")
        else:
            lines.append("Data planowana w Eskulapie: brak")
        if worker != "brak":
            lines.append(f"Pracownik: {worker}")
        return "\n".join(lines) if lines else "brak"
    if worker == "brak" and visit_type == "brak":
        return "brak"
    if worker == "brak":
        return visit_type
    if visit_type == "brak":
        return worker
    return f"{worker}\n{visit_type}"


def eskulap_visit_tooltip(record):
    details = eskulap_visit_details(record)
    if _uses_manual_kompas_planning(record):
        return (
            f"{details}\n\n"
            "Status „Zaplanowana” wynika wyłącznie z terminu zapisanego "
            "w KOMPAS. Data planowana w Eskulapie jest informacją źródłową "
            "i nie zapisuje terminu KOMPAS automatycznie."
        )
    return details
