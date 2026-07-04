from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class Patient:
    patient_id: str | int | None = None
    pesel: str | None = None
    last_name: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    birth_date: date | datetime | None = None
    sex: str | None = None
    phone: str | None = None
    email: str | None = None
    guardian_first_name: str | None = None
    guardian_last_name: str | None = None
    guardian_pesel: str | None = None
    guardian_phone: str | None = None
    guardian_email: str | None = None
    status: str | None = None
    death_date: date | datetime | None = None
