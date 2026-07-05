from dataclasses import dataclass

from app.models.event import Event


@dataclass(frozen=True)
class Visit(Event):
    parametr_kod: str | None = None
    parametr_nazwa: str | None = None
    parametr_czy_aktualne: str | None = None
