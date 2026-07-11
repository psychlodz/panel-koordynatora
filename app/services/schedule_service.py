import logging
from datetime import date, datetime

import pandas as pd

from app.gateway.eskulap_gateway import EskulapGateway
from app.repositories.visit_mapping_repository import list_visit_mappings


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
                "Data końcowa harmonogramu nie może być wcześniejsza niż data początkowa."
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

        rows = [
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
                "RODZAJE_WIZYT_LISTA": entry.rodzaje_wizyt_lista,
                "RODZAJE_WIZYT_NAZWY": self._visit_type_display_text(
                    entry.rodzaje_wizyt_lista
                ),
            }
            for entry in entries
        ]
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
                "RODZAJE_WIZYT_LISTA",
                "RODZAJE_WIZYT_NAZWY",
            ],
        )

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

    def _visit_type_name_map(self):
        if self._visit_type_names is None:
            names = {}
            try:
                for row in list_visit_mappings(only_active=True):
                    code = str(row.get("parametr_kod") or "").strip().upper()
                    name = str(
                        row.get("parametr_nazwa_cache") or ""
                    ).strip()
                    if code and name:
                        names[code] = name
            except Exception:
                logger.exception(
                    "Nie udało się pobrać lokalnego słownika rodzajów wizyt"
                )
                names = {}
            self._visit_type_names = names
        return self._visit_type_names

    def _visit_type_display_text(self, codes):
        codes = [
            str(code or "").strip().upper()
            for code in (codes or [])
            if str(code or "").strip()
        ]
        if not codes:
            return "Brak określonych rodzajów wizyt"
        names = self._visit_type_name_map()
        labels = []
        seen = set()
        for code in codes:
            label = names.get(code) or f"{code} — brak nazwy w słowniku"
            if label in seen:
                continue
            seen.add(label)
            labels.append(label)
        return "; ".join(sorted(labels, key=str.casefold))
