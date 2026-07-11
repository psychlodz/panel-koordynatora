import argparse
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.gateway.eskulap_gateway import EskulapGateway
from app.repositories.visit_type_dictionary_repository import (
    get_visit_type_names,
)
from config import load_config


def parse_args():
    today = date.today()
    cfg = load_config()
    parser = argparse.ArgumentParser(
        description="Test kodów rodzajów wizyt w harmonogramie pracy."
    )
    parser.add_argument("--jo-id", default=cfg.default_jo_id)
    parser.add_argument(
        "--date-from",
        default=today.replace(day=1).isoformat(),
    )
    parser.add_argument("--date-to", default=today.isoformat())
    return parser.parse_args()


def main():
    args = parse_args()
    rows = EskulapGateway().get_work_schedule(
        jo_id=args.jo_id,
        date_from=args.date_from,
        date_to=args.date_to,
    )
    print("Widok Oracle: ESK_RAPORTY.V_KOMPAS_PLAN_PRACY_KALENDARZ")
    print(f"Liczba rekordów: {len(rows)}")

    duplicate_pln_ids = []
    seen_pln_ids = set()
    for row in rows:
        if row.pln_id in seen_pln_ids:
            duplicate_pln_ids.append(row.pln_id)
        seen_pln_ids.add(row.pln_id)

        codes = row.rodzaje_wizyt_lista
        names = get_visit_type_names(codes)
        if len(codes) != len(set(codes)):
            raise AssertionError(
                f"PLN_ID={row.pln_id} ma zduplikowane kody: {codes}"
            )
        decoded = [
            f"{code}={names.get(code, 'brak w lokalnym słowniku')}"
            for code in codes
        ]
        print(
            f"PLN_ID={row.pln_id}; pracownik={row.pracownik}; "
            f"kody={', '.join(codes) if codes else 'brak'}; "
            f"oracle_nazwy={row.rodzaje_wizyt or 'brak'}; "
            f"lokalny_słownik={'; '.join(decoded) if decoded else 'brak'}"
        )

    if duplicate_pln_ids:
        raise AssertionError(
            "Wynik zawiera powielone PLN_ID: "
            + ", ".join(str(value) for value in duplicate_pln_ids[:20])
        )


if __name__ == "__main__":
    main()
