from dataclasses import fields

from app.models.consultation import Consultation
from app.models.event import Event
from app.models.imaging_order import ImagingOrder
from app.models.laboratory_order import LaboratoryOrder
from app.models.organizational_unit import OrganizationalUnit
from app.models.patient import Patient
from app.models.qualification_visit import QualificationVisit
from app.models.visit import Visit
from app.repositories import (
    event_repository,
    organizational_unit_repository,
    patient_repository,
    qualification_repository,
)


PATIENT_FIELDS = {
    "patient_id": "pacjent_id",
    "pesel": "pesel",
    "last_name": "nazwisko",
    "first_name": "imie",
    "middle_name": "drugie_imie",
    "birth_date": "data_urodzenia",
    "sex": "plec",
    "phone": "telefon",
    "email": "email",
    "guardian_first_name": "opiekun_imie",
    "guardian_last_name": "opiekun_nazwisko",
    "guardian_pesel": "opiekun_pesel",
    "guardian_phone": "opiekun_telefon",
    "guardian_email": "opiekun_email",
    "status": "status_pacjenta",
    "death_date": "data_zgonu",
}

QUALIFICATION_VISIT_FIELDS = {
    "visit_id": "wizyta_id",
    "patient_id": "pacjent_id",
    "pesel": "pesel",
    "last_name": "nazwisko",
    "first_name": "imie",
    "visit_date": "data_wizyty",
    "clinic_id": "poradnia_id",
    "clinic_code": "poradnia_symbol",
    "clinic_name": ("poradnia", "poradnia_nazwa"),
    "employee_id": "pracownik_id",
    "employee_name": "pracownik",
    "visit_type": "typ_wizyty",
    "visit_status": ("status_wizyty", "decyzja"),
    "description": "opis",
    "episode_id": "epizod_id",
    "assignment_status": "assignment_status",
}


def _source_value(row, source_fields):
    if isinstance(source_fields, str):
        source_fields = (source_fields,)
    for source_field in source_fields:
        value = row.get(source_field)
        if value is not None:
            return value
    return None


def _mapping_to_model(model_class, row, field_mapping):
    if row is None:
        return None
    field_names = {field.name for field in fields(model_class)}
    return model_class(
        **{
            model_field: _source_value(row, source_fields)
            for model_field, source_fields in field_mapping.items()
            if model_field in field_names
        }
    )


def _event_to_model(model_class, event: Event):
    return model_class(
        **{
            field.name: getattr(event, field.name)
            for field in fields(Event)
        }
    )


class EskulapGateway:
    """Publiczny punkt odczytu danych Eskulapa przez repozytoria."""

    def __init__(
        self,
        patients=patient_repository,
        qualifications=qualification_repository,
        events=event_repository,
        units=organizational_unit_repository,
    ):
        # Repozytoria korzystają z fabryki połączeń z db.py. Gateway nie
        # otwiera połączeń i nie zna SQL ani nazw widoków Oracle.
        self._patients = patients
        self._qualifications = qualifications
        self._events = events
        self._units = units

    def search_patients(self, search_text) -> list[Patient]:
        rows = self._patients.search_patients(search_text)
        return [
            _mapping_to_model(Patient, row, PATIENT_FIELDS)
            for row in rows
        ]

    def get_patient(self, patient_id) -> Patient | None:
        row = self._patients.get_patient(patient_id)
        return _mapping_to_model(Patient, row, PATIENT_FIELDS)

    def get_patient_visits(self, patient_id) -> list[Visit]:
        events = self._events.get_patient_visits(patient_id)
        return [
            _event_to_model(Visit, event)
            for event in events
        ]

    def get_patient_qualification_visits(
        self,
        date_from=None,
        date_to=None,
        only_unassigned=True,
    ) -> list[QualificationVisit]:
        rows = self._qualifications.list_qualification_visits(
            date_from,
            date_to,
            only_unassigned,
        )
        return [
            _mapping_to_model(
                QualificationVisit,
                row,
                QUALIFICATION_VISIT_FIELDS,
            )
            for row in rows
        ]

    def get_patient_consultations(
        self,
        patient_id,
    ) -> list[Consultation]:
        events = self._events.get_patient_consultations(patient_id)
        return [
            _event_to_model(Consultation, event)
            for event in events
        ]

    def get_patient_laboratory_orders(
        self,
        patient_id,
    ) -> list[LaboratoryOrder]:
        events = self._events.get_patient_laboratory_orders(patient_id)
        return [
            _event_to_model(LaboratoryOrder, event)
            for event in events
        ]

    def get_patient_imaging_orders(
        self,
        patient_id,
    ) -> list[ImagingOrder]:
        events = self._events.get_patient_imaging_orders(patient_id)
        return [
            _event_to_model(ImagingOrder, event)
            for event in events
        ]

    def list_organizational_units(
        self,
        search_text=None,
    ) -> list[OrganizationalUnit]:
        rows = self._units.list_organizational_units(search_text)
        return [
            OrganizationalUnit(
                jo_id=str(row["jo_id"]),
                jo_symbol=_source_value(row, "jo_symbol"),
                jo_nazwa=_source_value(row, "jo_nazwa"),
            )
            for row in rows
        ]
