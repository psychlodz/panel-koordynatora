import argparse
import sys
from contextlib import closing
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.repositories.db_connection import (
    create_connection,
    load_database_settings,
)
from scripts.check_polish_chars import (
    SUSPICIOUS_CHARACTERS,
    TEXT_COLUMNS,
    find_suspicious_records,
)


def _suspicious_score(value):
    return sum(value.count(character) for character in SUSPICIOUS_CHARACTERS)


def repair_text(value):
    if not isinstance(value, str):
        return value

    current = value
    for _attempt in range(3):
        candidates = []
        # CP1250 odpowiada typowemu przypadkowi: poprawny tekst UTF-8
        # został błędnie odczytany przez polską stronę kodową Windows.
        for source_encoding in ("cp1250", "cp1252", "latin1"):
            try:
                candidate = current.encode(source_encoding).decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
            if "\ufffd" not in candidate:
                candidates.append(candidate)
        if not candidates:
            break

        best = min(candidates, key=_suspicious_score)
        if _suspicious_score(best) >= _suspicious_score(current):
            break
        current = best
    return current


def proposed_changes(connection):
    changes = []
    for finding in find_suspicious_records(connection):
        repaired = repair_text(finding["value"])
        if (
            repaired != finding["value"]
            and _suspicious_score(repaired)
            < _suspicious_score(finding["value"])
        ):
            changes.append({**finding, "new_value": repaired})
    return changes


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Kontrolowana naprawa podwójnie zakodowanych tekstów "
            "w tabelach konfiguracyjnych KOMPAS."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Zastosuj wypisane poprawki w jednej transakcji.",
    )
    args = parser.parse_args()
    if not args.apply:
        parser.error(
            "Skrypt nie modyfikuje danych bez jawnego parametru --apply."
        )

    try:
        settings = load_database_settings()
        if settings.engine != "postgres":
            raise RuntimeError(
                "Naprawa wymaga konfiguracji engine=postgres."
            )
        with closing(create_connection(settings)) as connection:
            changes = proposed_changes(connection)
            if not changes:
                print("Brak tekstów, które można bezpiecznie poprawić.")
                return 0

            print("Proponowane zmiany:")
            for change in changes:
                print(
                    f"- {change['table']}.{change['column']} "
                    f"({change['primary_key']}={change['record_id']}): "
                    f"{change['value']!r} -> {change['new_value']!r}"
                )

            try:
                for change in changes:
                    allowed_columns = TEXT_COLUMNS[change["table"]][1]
                    if change["column"] not in allowed_columns:
                        raise RuntimeError("Niedozwolona kolumna naprawy")
                    connection.execute(
                        f"""
                        UPDATE {change['table']}
                        SET {change['column']} = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE {change['primary_key']} = ?
                        """,
                        (
                            change["new_value"],
                            change["record_id"],
                        ),
                    )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
    except Exception as exc:
        print(f"BŁĄD: {exc}", file=sys.stderr)
        return 2

    print(f"Zastosowano zmian: {len(changes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
