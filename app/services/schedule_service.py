import logging
from calendar import monthrange
from datetime import date, datetime, time

import pandas as pd

from app.gateway.eskulap_gateway import EskulapGateway
from app.models.work_schedule import normalize_visit_type_code
from app.repositories.visit_type_dictionary_repository import (
    get_visit_type_names,
)


logger = logging.getLogger(__name__)


class ScheduleService:
    """Warstwa modułu Harmonogram pracy ukrywająca szczegóły Eskulapa."""

    def __init__(self, gateway=None):
        self.gateway = gateway or EskulapGateway()
        self._visit_type_names = None

    def list_organizational_units(self, search_text=None) -> pd.DataFrame:
        try:
            units = self.gateway.list_organizational_units(search_text)
        except Exception as exc:
            logger.exception(
                "Błąd pobierania jednostek organizacyjnych przez Gateway"
            )
            raise RuntimeError(
                "Nie udało się pobrać listy jednostek z Eskulapa."
            ) from exc

        rows = [
            {
                "JO_ID": unit.jo_id,
                "JO_SYMBOL": unit.jo_symbol,
                "JO_NAZWA": unit.jo_nazwa,
            }
            for unit in units
        ]
        return pd.DataFrame(rows, columns=["JO_ID", "JO_SYMBOL", "JO_NAZWA"])

    def get_work_schedule(
        self,
        jo_id,
        date_from,
        date_to,
        employee_ids=None,
    ) -> pd.DataFrame:
        date_from = self._date_value(date_from, "date_from")
        date_to = self._date_value(date_to, "date_to")
        if date_from > date_to:
            raise ValueError(
                "Data końcowa harmonogramu nie może być wcześniejsza "
                "niż data początkowa."
            )

        try:
            entries = self.gateway.get_work_schedule(
                jo_id=jo_id,
                date_from=date_from,
                date_to=date_to,
                employee_ids=employee_ids,
            )
        except Exception as exc:
            logger.exception(
                "Błąd pobierania harmonogramu pracy przez Gateway"
            )
            raise RuntimeError(
                "Nie udało się pobrać harmonogramu pracy z Eskulapa."
            ) from exc

        all_visit_type_codes = sorted(
            {
                str(code or "").strip().upper()
                for entry in entries
                if not entry.rodzaje_wizyt_nazwy_lista
                for code in (entry.rodzaje_wizyt_lista or [])
                if str(code or "").strip()
            }
        )
        visit_type_names = self._visit_type_name_map(all_visit_type_codes)

        rows = []
        for entry in entries:
            visit_types_text, visit_types_tooltip = self._visit_type_display(
                entry.rodzaje_wizyt_lista,
                visit_type_names,
                entry.rodzaje_wizyt_nazwy_lista,
            )
            rows.append(
                {
                    "JO_ID": entry.jo_id,
                    "JO_SYMBOL": entry.jo_symbol,
                    "JO_NAZWA": entry.jo_nazwa,
                    "DATA_DNIA": entry.data_dnia,
                    "DATA_TEKST": entry.data_tekst,
                    "DZIEN_TYG": entry.dzien_tyg,
                    "PRACOWNIK_ID": entry.pracownik_id,
                    "PRACOWNIK": entry.pracownik,
                    "GODZ_OD": entry.godz_od,
                    "GODZ_DO": entry.godz_do,
                    "PLN_ID": entry.pln_id,
                    "PLN_OPIS": entry.pln_opis,
                    "RODZAJE_WIZYT_KODY": entry.rodzaje_wizyt_kody,
                    "RODZAJE_WIZYT": entry.rodzaje_wizyt,
                    "RODZAJE_WIZYT_LISTA": entry.rodzaje_wizyt_lista,
                    "RODZAJE_WIZYT_NAZWY": visit_types_text,
                    "RODZAJE_WIZYT_TOOLTIP": visit_types_tooltip,
                }
            )
        return pd.DataFrame(
            rows,
            columns=[
                "JO_ID",
                "JO_SYMBOL",
                "JO_NAZWA",
                "DATA_DNIA",
                "DATA_TEKST",
                "DZIEN_TYG",
                "PRACOWNIK_ID",
                "PRACOWNIK",
                "GODZ_OD",
                "GODZ_DO",
                "PLN_ID",
                "PLN_OPIS",
                "RODZAJE_WIZYT_KODY",
                "RODZAJE_WIZYT",
                "RODZAJE_WIZYT_LISTA",
                "RODZAJE_WIZYT_NAZWY",
                "RODZAJE_WIZYT_TOOLTIP",
            ],
        )

    def get_visit_type_month_calendar(
        self,
        jo_id,
        year,
        month,
        visit_type_filter="",
        only_available=True,
    ) -> dict:
        year = int(year)
        month = int(month)
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])

        try:
            records = self.gateway.get_visit_type_availability(
                jo_id=jo_id,
                date_from=first_day,
                date_to=last_day,
            )
        except Exception as exc:
            logger.exception(
                "Błąd pobierania dostępności rodzajów wizyt przez Gateway"
            )
            raise RuntimeError(
                "Nie udało się pobrać dostępności rodzajów wizyt z Eskulapa."
            ) from exc

        return build_visit_type_month_calendar(
            records,
            year,
            month,
            visit_type_filter=visit_type_filter,
            only_available=only_available,
            visit_parameters=(
                [] if only_available else self._safe_visit_parameters()
            ),
        )

    def _safe_visit_parameters(self):
        try:
            return self.gateway.list_visit_parameters(only_active=True)
        except Exception:
            logger.exception(
                "Nie udało się pobrać listy rodzajów wizyt z Gateway"
            )
            return []

    @staticmethod
    def _date_value(value, field_name):
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

    def _visit_type_name_map(self, codes):
        key = tuple(sorted(set(codes or [])))
        if self._visit_type_names is None:
            self._visit_type_names = {}
        if key not in self._visit_type_names:
            try:
                self._visit_type_names[key] = get_visit_type_names(key)
            except Exception:
                logger.exception(
                    "Nie udało się pobrać lokalnego słownika rodzajów wizyt"
                )
                self._visit_type_names[key] = {}
        return self._visit_type_names[key]

    @staticmethod
    def _visit_type_display(codes, names, oracle_names=None):
        oracle_names = [
            str(name or "").strip()
            for name in (oracle_names or [])
            if str(name or "").strip()
        ]
        if oracle_names:
            display = "\n".join(
                sorted(dict.fromkeys(oracle_names), key=str.casefold)
            )
            return display, display

        codes = [
            str(code or "").strip().upper()
            for code in (codes or [])
            if str(code or "").strip()
        ]
        if not codes:
            text = "Brak określonych rodzajów wizyt"
            return text, text

        labels = []
        seen = set()
        for code in codes:
            if code in names and str(names[code] or "").strip():
                label = str(names[code]).strip()
            else:
                label = f"{code} — brak nazwy rodzaju wizyty"
            if label in seen:
                continue
            seen.add(label)
            labels.append(label)

        display = "\n".join(sorted(labels, key=str.casefold))
        return display, display


def _as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _as_minutes(value):
    if value is None or str(value).strip() == "":
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, datetime):
        return value.hour * 60 + value.minute
    if isinstance(value, time):
        return value.hour * 60 + value.minute
    text = str(value).strip()
    if ":" in text:
        hour, minute = text[:5].split(":")
        return int(hour) * 60 + int(minute)
    return int(float(text))


def _minutes_to_text(value):
    value = int(value)
    return f"{value // 60:02d}:{value % 60:02d}"


def _record_start_minutes(record):
    value = _as_minutes(getattr(record, "minuta_od", None))
    if value is None:
        value = _as_minutes(getattr(record, "godz_od", None))
    return value


def _record_end_minutes(record):
    value = _as_minutes(getattr(record, "minuta_do", None))
    if value is None:
        value = _as_minutes(getattr(record, "godz_do", None))
    return value


def merge_time_ranges(ranges):
    normalized = sorted(
        (int(start), int(end))
        for start, end in ranges
        if start is not None and end is not None and int(start) < int(end)
    )
    if not normalized:
        return []

    merged = [list(normalized[0])]
    for start, end in normalized[1:]:
        current = merged[-1]
        if start <= current[1]:
            current[1] = max(current[1], end)
        else:
            merged.append([start, end])
    return [tuple(item) for item in merged]


def _visit_type_label(record):
    code = normalize_visit_type_code(getattr(record, "parametr_kod", None))
    name = str(getattr(record, "parametr_nazwa", "") or "").strip()
    if name:
        return name
    return f"{code} — brak nazwy rodzaju wizyty"


def _availability_detail(record, all_plan_records):
    plan_records = all_plan_records.get(
        (
            _as_date(record.data_dnia),
            str(record.pln_id),
            str(record.pracownik_id),
            _record_start_minutes(record),
            _record_end_minutes(record),
        ),
        [record],
    )
    labels = sorted(
        dict.fromkeys(_visit_type_label(item) for item in plan_records),
        key=str.casefold,
    )
    start = _record_start_minutes(record)
    end = _record_end_minutes(record)
    return {
        "pracownik": str(record.pracownik or "[bez pracownika]"),
        "pracownik_id": record.pracownik_id,
        "pln_id": record.pln_id,
        "godz_od": _minutes_to_text(start),
        "godz_do": _minutes_to_text(end),
        "przedzial": f"{_minutes_to_text(start)}–{_minutes_to_text(end)}",
        "rodzaje_wizyt": "\n".join(labels),
        "tooltip": "\n".join(labels),
        "jo_id": record.jo_id,
        "jo_symbol": record.jo_symbol,
        "jo_nazwa": record.jo_nazwa,
    }


def _matches_visit_type_filter(code, name, visit_type_filter):
    pattern = str(visit_type_filter or "").strip().casefold()
    if not pattern:
        return True
    return pattern in str(code or "").casefold() or pattern in str(name or "").casefold()


def build_visit_type_month_calendar(
    records,
    year,
    month,
    visit_type_filter="",
    only_available=True,
    visit_parameters=None,
):
    days = [
        date(int(year), int(month), day)
        for day in range(1, monthrange(int(year), int(month))[1] + 1)
    ]

    plan_records = {}
    for record in records:
        try:
            key = (
                _as_date(record.data_dnia),
                str(record.pln_id),
                str(record.pracownik_id),
                _record_start_minutes(record),
                _record_end_minutes(record),
            )
        except Exception:
            logger.exception("Pominięto niepoprawny rekord dostępności")
            continue
        plan_records.setdefault(key, []).append(record)

    rows_by_code = {}
    for record in records:
        code = normalize_visit_type_code(record.parametr_kod)
        if not code:
            continue
        name = str(record.parametr_nazwa or "").strip()
        if not _matches_visit_type_filter(code, name, visit_type_filter):
            continue
        row = rows_by_code.setdefault(
            code,
            {
                "code": code,
                "name": name or f"{code} — brak nazwy rodzaju wizyty",
                "cells": {
                    day: {
                        "text": "",
                        "tooltip": "",
                        "details": [],
                        "ranges": [],
                    }
                    for day in days
                },
            },
        )
        if name and row["name"].startswith(code):
            row["name"] = name
        day = _as_date(record.data_dnia)
        if day not in row["cells"]:
            continue
        start = _record_start_minutes(record)
        end = _record_end_minutes(record)
        if start is None or end is None:
            continue
        cell = row["cells"][day]
        cell["ranges"].append((start, end))
        detail = _availability_detail(record, plan_records)
        detail_key = (
            str(detail["pln_id"]),
            str(detail["pracownik_id"]),
            detail["godz_od"],
            detail["godz_do"],
        )
        if detail_key not in {
            (
                str(item["pln_id"]),
                str(item["pracownik_id"]),
                item["godz_od"],
                item["godz_do"],
            )
            for item in cell["details"]
        }:
            cell["details"].append(detail)

    if not only_available:
        for parameter in visit_parameters or []:
            code = normalize_visit_type_code(getattr(parameter, "code", None))
            name = str(getattr(parameter, "name", "") or "").strip()
            if not code or not _matches_visit_type_filter(code, name, visit_type_filter):
                continue
            rows_by_code.setdefault(
                code,
                {
                    "code": code,
                    "name": name or f"{code} — brak nazwy rodzaju wizyty",
                    "cells": {
                        day: {
                            "text": "",
                            "tooltip": "",
                            "details": [],
                            "ranges": [],
                        }
                        for day in days
                    },
                },
            )

    for row in rows_by_code.values():
        for cell in row["cells"].values():
            merged = merge_time_ranges(cell.pop("ranges", []))
            lines = [
                f"{_minutes_to_text(start)}–{_minutes_to_text(end)}"
                for start, end in merged
            ]
            cell["text"] = "\n".join(lines)
            cell["tooltip"] = cell["text"]
            cell["details"].sort(
                key=lambda item: (
                    item["godz_od"],
                    str(item["pracownik"] or "").casefold(),
                )
            )

    rows = sorted(
        rows_by_code.values(),
        key=lambda row: (
            int(row["code"][1:]) if str(row["code"]).startswith("F") and str(row["code"])[1:].isdigit() else 999,
            str(row["code"]),
        ),
    )
    return {
        "year": int(year),
        "month": int(month),
        "days": days,
        "rows": rows,
    }
