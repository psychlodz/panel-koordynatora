from dataclasses import dataclass, field


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
    rodzaje_wizyt_lista: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.rodzaje_wizyt_lista:
            object.__setattr__(
                self,
                "rodzaje_wizyt_lista",
                _split_visit_type_codes(self.rodzaje_wizyt_kody),
            )
