from dataclasses import dataclass

from app.models.event import Event


@dataclass(frozen=True)
class Consultation(Event):
    pass
