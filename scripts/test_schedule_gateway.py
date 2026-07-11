import argparse
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.gateway.eskulap_gateway import EskulapGateway
from config import load_config


REQUIRED_FIELDS = [
    "jo_id",
    "jo_symbol",
    "jo_nazwa",
    "data_dnia",
    "data_tekst",
    "dzien_tyg",
    "pracownik_id",
    "pracownik",
    "godz_od",
    "godz_do",
    "pln_id",
    "pln_opis",
    "rodzaje_wizyt_kody",
    "rodzaje_wizyt_lista",
]


def parse_args():
    today = date.today()
    cfg = load_config()
    parser = argparse.ArgumentParser(
        description="Test odczytu harmonogramu przez EskulapGateway."
    )
    parser.add_argument(
        "--jo-id",
        default=cfg.default_jo_id,
        help="Identyfikator jednostki organizacyjnej.",
    )
    parser.add_argument(
        "--date-from",
        default=today.replace(day=1).isoformat(),
        help="Data od w formacie RRRR-MM-DD.",
    )
    parser.add_argument(
        "--date-to",
        default=today.isoformat(),
        help="Data do w formacie RRRR-MM-DD.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    gateway = EskulapGateway()
    rows = gateway.get_work_schedule(
        jo_id=args.jo_id,
        date_from=args.date_from,
        date_to=args.date_to,
    )

    print("Widok Oracle: ESK_RAPORTY.V_KOMPAS_PLAN_PRACY_KALENDARZ")
    print(
        f"Zakres: jo_id={args.jo_id}, "
        f"od={args.date_from}, do={args.date_to}"
    )
    print(f"Liczba rekordów: {len(rows)}")

    if rows:
        first = rows[0]
        missing = [
            field
            for field in REQUIRED_FIELDS
            if not hasattr(first, field)
        ]
        if missing:
            raise AssertionError(
                "Brak wymaganych pól: " + ", ".join(missing)
            )
        print("Pierwszy rekord:")
        for field in REQUIRED_FIELDS:
            print(f"  {field}: {getattr(first, field)}")
        codes = getattr(first, "rodzaje_wizyt_lista")
        if len(codes) != len(set(codes)):
            raise AssertionError(
                "Lista rodzajów wizyt zawiera duplikaty: "
                + ", ".join(codes)
            )
    else:
        print(
            "Brak rekordów w podanym zakresie; połączenie i wywołanie Gateway "
            "zakończone poprawnie."
        )


if __name__ == "__main__":
    main()
