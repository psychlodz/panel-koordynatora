from dataclasses import dataclass


@dataclass(frozen=True)
class WorkScheduleEntry:
    """Pojedynczy rekord planu pracy pobrany z Eskulapa."""

    jo_id: object = None
    jo_symbol: str | None = None
    jo_nazwa: str | None = None
    data_dnia: object = None
    dzien_tyg: str | None = None
    pracownik_id: object = None
    pracownik: str | None = None
    godz_od: object = None
    godz_do: object = None
    pln_id: object = None
