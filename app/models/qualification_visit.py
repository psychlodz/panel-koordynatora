from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class QualificationVisit:
    visit_id: str | int | None = None
    patient_id: str | int | None = None
    pesel: str | None = None
    last_name: str | None = None
    first_name: str | None = None
    visit_date: date | datetime | None = None
    clinic_id: str | int | None = None
    clinic_code: str | None = None
    clinic_name: str | None = None
    employee_id: str | int | None = None
    employee_name: str | None = None
    visit_type: str | None = None
    visit_status: str | None = None
    description: str | None = None
    episode_id: int | None = None
    assignment_status: str | None = None
