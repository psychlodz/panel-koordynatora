from dataclasses import dataclass

from app.models.event import Event


@dataclass(frozen=True)
class LaboratoryOrder(Event):
    pass
