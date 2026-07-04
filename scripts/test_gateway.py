import argparse
import sys
from dataclasses import asdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.gateway.eskulap_gateway import EskulapGateway
from app.repositories.event_repository import EXAMS_VIEW
from app.repositories.qualification_repository import QUALIFICATION_VIEW


def _print_collection(label, items):
    print(f"\n{label} ({len(items)}):")
    for item in items:
        print(asdict(item))


def _test_collection(label, loader, source_view=None):
    if source_view:
        print(f"\nWidok Oracle: {source_view}")
    try:
        items = loader()
    except Exception as exc:
        print(f"\n{label}: BŁĄD")
        print(f"{type(exc).__name__}: {exc}")
        return None
    _print_collection(label, items)
    return items


def main():
    parser = argparse.ArgumentParser(
        description="Ręczny test odczytu danych przez EskulapGateway."
    )
    parser.add_argument(
        "search_text",
        help="Fragment nazwiska albo numeru PESEL pacjenta.",
    )
    parser.add_argument("--date-from", help="Początek okresu RRRR-MM-DD.")
    parser.add_argument("--date-to", help="Koniec okresu RRRR-MM-DD.")
    args = parser.parse_args()

    gateway = EskulapGateway()
    patients = gateway.search_patients(args.search_text)
    _print_collection("Pacjenci", patients)
    if not patients:
        print("\nNie znaleziono pacjenta.")
        return

    patient = gateway.get_patient(patients[0].patient_id)
    print("\nWybrany pacjent:")
    print(asdict(patient) if patient else None)

    patient_id = patients[0].patient_id
    _test_collection(
        "Wizyty",
        lambda: gateway.get_patient_visits(patient_id),
    )
    _test_collection(
        "Konsultacje",
        lambda: gateway.get_patient_consultations(patient_id),
    )
    _test_collection(
        "Zlecenia laboratoryjne",
        lambda: gateway.get_patient_laboratory_orders(patient_id),
        EXAMS_VIEW,
    )
    _test_collection(
        "Zlecenia obrazowe",
        lambda: gateway.get_patient_imaging_orders(patient_id),
        EXAMS_VIEW,
    )
    _test_collection(
        "Wizyty kwalifikacyjne",
        lambda: gateway.get_patient_qualification_visits(
            date_from=args.date_from,
            date_to=args.date_to,
        ),
        QUALIFICATION_VIEW,
    )


if __name__ == "__main__":
    main()
