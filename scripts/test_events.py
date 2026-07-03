import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.repositories.event_repository import (
    get_patient_consultations,
    get_patient_imaging_orders,
    get_patient_laboratory_orders,
    get_patient_visits,
)


def _print_events(title, events):
    print(f"\n{title} ({len(events)}):")
    print(
        json.dumps(
            [asdict(event) for event in events],
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


def main():
    parser = argparse.ArgumentParser(
        description="Test wspólnego repozytorium zdarzeń Eskulapa."
    )
    parser.add_argument("patient_id", help="Identyfikator pacjenta w Eskulapie.")
    parser.add_argument("--date-from")
    parser.add_argument("--date-to")
    args = parser.parse_args()

    query_args = (args.patient_id, args.date_from, args.date_to)
    _print_events("Wizyty", get_patient_visits(*query_args))
    _print_events("Konsultacje", get_patient_consultations(*query_args))
    _print_events(
        "Zlecenia laboratoryjne",
        get_patient_laboratory_orders(*query_args),
    )
    _print_events(
        "Zlecenia obrazowe",
        get_patient_imaging_orders(*query_args),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
