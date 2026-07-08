import os
import re
import sys
import unicodedata
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


SEED_PATH = PROJECT_ROOT / "db" / "postgres" / "004_seed.sql"

EXPECTED_BLOCKS = {
    "KONSULTACJA_PSYCHIATRYCZNA_KOMPLEKSOWA",
    "KONSULTACJA_PSYCHIATRYCZNA_DIAGNOSTYCZNA",
    "KONSULTACJA_PSYCHIATRYCZNA_TERAPEUTYCZNA",
    "KONSULTACJA_PSYCHOLOGICZNA_DIAGNOSTYCZNA",
    "KONSULTACJA_PSYCHOLOGICZNA_TERAPEUTYCZNA",
    "KONSULTACJA_TERAPEUTY_SRODOWISKOWEGO",
    "SUPERWIZJA",
    "SESJA_TERAPEUTYCZNA_GRUPOWA",
    "SESJA_PSYCHOLOGICZNA",
    "SESJA_PSYCHOLOGICZNA_GRUPOWA",
    "SESJA_PSYCHOTERAPEUTYCZNA",
    "SESJA_PSYCHOTERAPEUTYCZNA_GRUPOWA",
}

REPLACED_BLOCKS = {
    "WIZYTA_PSYCHIATRYCZNA",
    "PSYCHOTERAPIA",
}


def _has_polish_characters(text):
    return any(
        unicodedata.category(character).startswith("L")
        and ord(character) > 127
        for character in text
    )


def _extract_seed_blocks():
    text = SEED_PATH.read_text(encoding="utf-8")
    pattern = re.compile(
        r"\(\s*'(?P<kod>[A-Z0-9_]+)'\s*,\s*'(?P<nazwa>[^']+)'\s*,"
        r"\s*'(?P<opis>[^']*)'\s*,\s*'(?P<typ>[A-Z0-9_]+)'\s*,"
        r"\s*'(?P<grupa>[A-Z0-9_]+)'\s*,\s*'(?P<ikona>[^']*)'\s*,"
        r"\s*(?P<wymaga>[01])\s*,\s*(?P<obowiazkowy>[01])\s*,"
        r"\s*(?P<kolejnosc>[0-9]+)\s*\)",
        re.MULTILINE,
    )
    return {
        match.group("kod"): match.groupdict()
        for match in pattern.finditer(text)
    }


def test_seed_blocks():
    blocks = _extract_seed_blocks()
    missing = EXPECTED_BLOCKS - set(blocks)
    if missing:
        raise AssertionError(
            "Brakuje nowych klocków w seedzie: "
            + ", ".join(sorted(missing))
        )

    active_replaced = REPLACED_BLOCKS & set(blocks)
    if active_replaced:
        raise AssertionError(
            "Stare kody nie powinny być aktywnymi klockami w seedzie: "
            + ", ".join(sorted(active_replaced))
        )

    for code in EXPECTED_BLOCKS:
        block = blocks[code]
        if _has_polish_characters(code):
            raise AssertionError(f"Kod klocka zawiera polskie znaki: {code}")
        if not block["typ"] or not block["grupa"]:
            raise AssertionError(f"Klocek {code} nie ma typu lub grupy.")
        if block["typ"] not in {"KONSULTACJA", "SESJA"}:
            raise AssertionError(
                f"Klocek {code} ma nieoczekiwany typ: {block['typ']}"
            )
        if block["grupa"] not in {
            "KONSULTACJE",
            "PSYCHOTERAPIA",
            "DIAGNOSTYKA",
        }:
            raise AssertionError(
                f"Klocek {code} ma nieoczekiwaną grupę: {block['grupa']}"
            )
    print("Seed PostgreSQL - nowe klocki: OK")
    print("Seed PostgreSQL - stare kody zastapione: OK")
    print("Seed PostgreSQL - typy, grupy i kody ASCII: OK")


def test_live_postgres(dsn):
    from app.repositories.db_connection import DatabaseSettings, create_connection

    connection = create_connection(
        DatabaseSettings(engine="postgres", postgres_dsn=dsn)
    )
    try:
        rows = connection.execute(
            """
            SELECT k.kod, typ.kod AS typ_kod, grupa.kod AS grupa_kod
            FROM pk_klocki k
            JOIN pk_typy_elementow typ
                ON typ.typ_id = k.typ_elementu_id
            JOIN pk_grupy_klockow grupa
                ON grupa.grupa_id = k.grupa_id
            WHERE k.kod IN (
                'KONSULTACJA_PSYCHIATRYCZNA_KOMPLEKSOWA',
                'KONSULTACJA_PSYCHIATRYCZNA_DIAGNOSTYCZNA',
                'KONSULTACJA_PSYCHIATRYCZNA_TERAPEUTYCZNA',
                'KONSULTACJA_PSYCHOLOGICZNA_DIAGNOSTYCZNA',
                'KONSULTACJA_PSYCHOLOGICZNA_TERAPEUTYCZNA',
                'KONSULTACJA_TERAPEUTY_SRODOWISKOWEGO',
                'SUPERWIZJA',
                'SESJA_TERAPEUTYCZNA_GRUPOWA',
                'SESJA_PSYCHOLOGICZNA',
                'SESJA_PSYCHOLOGICZNA_GRUPOWA',
                'SESJA_PSYCHOTERAPEUTYCZNA',
                'SESJA_PSYCHOTERAPEUTYCZNA_GRUPOWA'
            )
              AND k.czy_aktywny = 1
            """
        ).fetchall()
        found = {row["kod"] for row in rows}
        missing = EXPECTED_BLOCKS - found
        if missing:
            raise AssertionError(
                "Brakuje aktywnych klocków w PostgreSQL: "
                + ", ".join(sorted(missing))
            )

        active_old = connection.execute(
            """
            SELECT kod
            FROM pk_klocki
            WHERE kod IN ('WIZYTA_PSYCHIATRYCZNA', 'PSYCHOTERAPIA')
              AND czy_aktywny = 1
            """
        ).fetchall()
        if active_old:
            raise AssertionError(
                "Stare kody nadal są aktywne w PostgreSQL: "
                + ", ".join(row["kod"] for row in active_old)
            )
    finally:
        connection.close()
    print("PostgreSQL - biblioteka klockow: OK")


def main():
    test_seed_blocks()
    dsn = os.environ.get("KOMPAS_TEST_POSTGRES_DSN", "").strip()
    if dsn:
        test_live_postgres(dsn)
    else:
        print(
            "Test PostgreSQL pominiety. Ustaw KOMPAS_TEST_POSTGRES_DSN, "
            "aby sprawdzic zywa baze."
        )


if __name__ == "__main__":
    main()
