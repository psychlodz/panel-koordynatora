from app.models.event import Event
from app.models.visit import Visit
from app.repositories.patient_repository import (
    CONSULTATIONS_VIEW,
    EXAMS_VIEW,
    VISITS_VIEW,
    get_patient_consultations as _get_patient_consultations,
    get_patient_exams as _get_patient_exams,
    get_patient_visits as _get_patient_visits,
)


EVENT_VISIT = "VISIT"
EVENT_CONSULTATION = "CONSULTATION"
EVENT_LABORATORY_ORDER = "LABORATORY_ORDER"
EVENT_IMAGING_ORDER = "IMAGING_ORDER"

LABORATORY_TYPES = {"L", "LAB", "LABORATORIUM"}
IMAGING_TYPES = {
    "R",
    "RTG",
    "USG",
    "TK",
    "CT",
    "MR",
    "MRI",
    "MAMMO",
    "MAMMOGRAFIA",
}


def _required_id(row: dict, field_name: str) -> str:
    value = row.get(field_name)
    if value is None or str(value).strip() == "":
        raise ValueError(f"Źródło Oracle nie zwróciło pola {field_name}")
    return str(value)


def _optional_text(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _description(row: dict, *field_names: str):
    for field_name in field_names:
        value = _optional_text(row.get(field_name))
        if value:
            return value
    return None


def _event(
    row,
    event_type,
    source,
    oracle_id_field,
    event_date,
    planned_date=None,
    description=None,
    status=None,
    model_class=Event,
    **model_fields,
) -> Event:
    oracle_id = _required_id(row, oracle_id_field)
    patient_id = _required_id(row, "pacjent_id")
    return model_class(
        event_id=f"{event_type}:{oracle_id}",
        patient_id=patient_id,
        event_type=event_type,
        source=source,
        status=_optional_text(status),
        event_date=event_date,
        planned_date=planned_date,
        description=_optional_text(description),
        oracle_id=oracle_id,
        **model_fields,
    )


def get_patient_visits(
    patient_id,
    date_from=None,
    date_to=None,
) -> list[Visit]:
    rows = _get_patient_visits(patient_id, date_from, date_to)
    return [
        _event(
            row,
            EVENT_VISIT,
            VISITS_VIEW,
            "wizyta_id",
            row.get("data_wizyty"),
            planned_date=row.get("data_planowana"),
            description=_description(
                row,
                "opis",
                "typ_wizyty",
                "poradnia_nazwa",
            ),
            status=row.get("decyzja"),
            model_class=Visit,
            parametr_kod=_optional_text(row.get("parametr_kod")),
            parametr_nazwa=_optional_text(row.get("parametr_nazwa")),
            parametr_czy_aktualne=_optional_text(
                row.get("parametr_czy_aktualne")
            ),
            employee_id=_optional_text(row.get("pracownik_id")),
            employee_name=_optional_text(row.get("pracownik")),
        )
        for row in rows
    ]


def get_patient_consultations(
    patient_id,
    date_from=None,
    date_to=None,
) -> list[Event]:
    rows = _get_patient_consultations(patient_id, date_from, date_to)
    return [
        _event(
            row,
            EVENT_CONSULTATION,
            CONSULTATIONS_VIEW,
            "konsultacja_id",
            row.get("data_przyjecia"),
            planned_date=row.get("data_planowana"),
            description=_description(row, "opis", "tytul", "uwagi"),
            status=row.get("status"),
        )
        for row in rows
    ]


def _exam_type(row):
    return str(row.get("typ") or "").strip().upper()


def _exam_event(row, event_type) -> Event:
    return _event(
        row,
        event_type,
        EXAMS_VIEW,
        "badanie_skierowanie_id",
        row.get("data_skierowania"),
        planned_date=(
            row.get("data_zaplanowana")
            or row.get("data_planowana_wykonania")
            or row.get("data_planowana")
        ),
        description=_description(
            row,
            "badanie_nazwa",
            "opis",
            "uwagi",
        ),
        status=row.get("status"),
    )


def get_patient_laboratory_orders(
    patient_id,
    date_from=None,
    date_to=None,
) -> list[Event]:
    rows = _get_patient_exams(patient_id, date_from, date_to)
    return [
        _exam_event(row, EVENT_LABORATORY_ORDER)
        for row in rows
        if _exam_type(row) in LABORATORY_TYPES
    ]


def get_patient_imaging_orders(
    patient_id,
    date_from=None,
    date_to=None,
) -> list[Event]:
    rows = _get_patient_exams(patient_id, date_from, date_to)
    return [
        _exam_event(row, EVENT_IMAGING_ORDER)
        for row in rows
        if _exam_type(row) in IMAGING_TYPES
    ]
