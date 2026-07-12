from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class Event:
    event_id: str
    patient_id: str
    event_type: str
    source: str
    status: str | None
    event_date: date | datetime | None
    planned_date: date | datetime | None
    description: str | None
    oracle_id: str
    realization_date: date | datetime | None = None
