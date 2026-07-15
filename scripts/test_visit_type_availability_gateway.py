import argparse
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.gateway.eskulap_gateway import EskulapGateway
from app.models.work_schedule import normalize_visit_type_code
from config import load_config


REQUIRED_FIELDS = [
    "jo_id",
    "jo_symbol",
    "jo_nazwa",
    "data_dnia",
    "pracownik_id",
    "pracownik",
    "pln_id",
    "plw_id",
    "parametr_kod",
    "parametr_nazwa",
    "godz_od",
    "godz_do",
    "minuta_od",
    "minuta_do",
]


def parse_args():
    today = date.today()
    cfg = load_config()
    parser = argparse.ArgumentParser(
        description="Test odczytu dostępności rodzajów wizyt przez EskulapGateway."
    )
    parser.add_argument("--jo-id", default=cfg.default_jo_id)
    parser.add_argument(
        "--date-from",
        default=today.replace(day=1).isoformat(),
    )
    parser.add_argument("--date-to", default=today.isoformat())
    parser.add_argument("--visit-type-code", action="append", default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    rows = EskulapGateway().get_visit_type_availability(
        jo_id=args.jo_id,
        date_from=args.date_from,
        date_to=args.date_to,
        visit_type_codes=args.visit_type_code,
    )
    print("Widok Oracle: ESK_RAPORTY.V_KOMPAS_DOSTEPNOSC_RODZAJOW_WIZYT")
    print(
        f"Zakres: jo_id={args.jo_id}, od={args.date_from}, do={args.date_to}"
    )
    print(f"Liczba rekordów: {len(rows)}")
    assert normalize_visit_type_code("F1") == "F01"

    if rows:
        first = rows[0]
        missing = [
            field
            for field in REQUIRED_FIELDS
            if not hasattr(first, field)
        ]
        if missing:
            raise AssertionError("Brak wymaganych pól: " + ", ".join(missing))
        for field in REQUIRED_FIELDS:
            print(f"  {field}: {getattr(first, field)}")
    else:
        print("Brak rekordów w podanym zakresie; wywołanie Gateway zakończone poprawnie.")


if __name__ == "__main__":
    main()
