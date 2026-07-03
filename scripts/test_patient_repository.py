import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.repositories.patient_repository import (
    get_patient,
    get_patient_consultations,
    get_patient_exams,
    get_patient_visits,
    search_patients,
)


def _print_json(title, value):
    print(f"\n{title}:")
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(
        description="Test repozytorium pacjentów Oracle KOMPAS."
    )
    parser.add_argument(
        "search_text",
        help="Fragment nazwiska albo numeru PESEL.",
    )
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--date-from")
    parser.add_argument("--date-to")
    args = parser.parse_args()

    patients = search_patients(args.search_text, args.limit)
    _print_json("Wyniki wyszukiwania", patients)
    if not patients:
        print("\nNie znaleziono pacjenta.")
        return 1

    pacjent_id = patients[0].get("pacjent_id")
    if pacjent_id is None:
        raise RuntimeError(
            "Widok V_KOMPAS_PACJENCI nie zwrócił kolumny PACJENT_ID"
        )

    patient = get_patient(pacjent_id)
    visits = get_patient_visits(
        pacjent_id,
        args.date_from,
        args.date_to,
    )
    consultations = get_patient_consultations(
        pacjent_id,
        args.date_from,
        args.date_to,
    )
    exams = get_patient_exams(
        pacjent_id,
        args.date_from,
        args.date_to,
    )

    _print_json("Szczegóły pacjenta", patient)
    _print_json("Wizyty", visits)
    _print_json("Konsultacje", consultations)
    _print_json("Badania", exams)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
