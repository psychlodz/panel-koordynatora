from dataclasses import dataclass, field
import re


def _split_visit_type_codes(value):
    result = []
    seen = set()
    for part in str(value or "").replace(";", ",").split(","):
        code = part.strip().upper()
        if not code or code in seen:
            continue
        seen.add(code)
        result.append(code)
    return result


def _split_visit_type_names(value):
    result = []
    seen = set()
    for part in str(value or "").split(";"):
        name = part.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        result.append(name)
    return result


def normalize_visit_type_code(value):
    text = str(value or "").strip().upper()
    match = re.fullmatch(r"F0?([1-9])", text)
    if match:
        return f"F0{match.group(1)}"
    return text


@dataclass(frozen=True)
class WorkScheduleEntry:
    """Pojedynczy rekord planu pracy pobrany z Eskulapa."""

    jo_id: object = None
    jo_symbol: str | None = None
    jo_nazwa: str | None = None
    data_dnia: object = None
    data_tekst: str | None = None
    dzien_tyg: str | None = None
    pracownik_id: object = None
    pracownik: str | None = None
    godz_od: object = None
    godz_do: object = None
    pln_id: object = None
    pln_opis: str | None = None
    rodzaje_wizyt_kody: str | None = None
    rodzaje_wizyt: str | None = None
    rodzaje_wizyt_lista: list[str] = field(default_factory=list)
    rodzaje_wizyt_nazwy_lista: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.rodzaje_wizyt_lista:
            object.__setattr__(
                self,
                "rodzaje_wizyt_lista",
                _split_visit_type_codes(self.rodzaje_wizyt_kody),
            )
        if not self.rodzaje_wizyt_nazwy_lista:
            object.__setattr__(
                self,
                "rodzaje_wizyt_nazwy_lista",
                _split_visit_type_names(self.rodzaje_wizyt),
            )


@dataclass(frozen=True)
class VisitTypeAvailabilityRecord:
    """Szczegółowy rekord dostępności rodzaju wizyty z Eskulapa."""

    jo_id: object = None
    jo_symbol: str | None = None
    jo_nazwa: str | None = None
    data_dnia: object = None
    pracownik_id: object = None
    pracownik: str | None = None
    pln_id: object = None
    plw_id: object = None
    parametr_kod: str | None = None
    parametr_nazwa: str | None = None
    godz_od: object = None
    godz_do: object = None
    minuta_od: object = None
    minuta_do: object = None

    def __post_init__(self):
        object.__setattr__(
            self,
            "parametr_kod",
            normalize_visit_type_code(self.parametr_kod),
        )
