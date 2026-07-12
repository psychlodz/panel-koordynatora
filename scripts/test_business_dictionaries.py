import os
import re
import sys
import unicodedata
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


SEED_PATH = PROJECT_ROOT / "db" / "postgres" / "004_seed.sql"
SCHEMA_PATH = PROJECT_ROOT / "db" / "postgres" / "003_schema.sql"
INDEX_PATH = PROJECT_ROOT / "db" / "postgres" / "005_indexes.sql"

EXPECTED_BLOCKS = {
    "PKK_KWAL",
    "PKK_WIZ",
    "KONSULTACJA_PSYCHIATRYCZNA_KOMPLEKSOWA",
    "KONSULTACJA_PSYCHIATRYCZNA_TERAPEUTYCZNA",
    "KONSULTACJA_PSYCHIATRYCZNA_DIAGNOSTYCZNA",
    "KONSULTACJA_TERAPEUTY_SRODOWISKOWEGO",
    "KONSULTACJA_PSYCHOLOGICZNA_DIAGNOSTYCZNA",
    "KONSULTACJA_PSYCHOLOGICZNA_TERAPEUTYCZNA",
    "KONSULTACJA_PSYCHOTERAPEUTYCZNA_DIAGNOSTYCZNA",
    "KONSULTACJA_PSYCHOTERAPEUTYCZNA_TERAPEUTYCZNA",
    "SESJA_TERAPEUTYCZNA",
    "SESJA_TERAPEUTYCZNA_GRUPOWA",
    "SESJA_PSYCHOLOGICZNA",
    "SESJA_PSYCHOLOGICZNA_GRUPOWA",
    "SESJA_PSYCHOTERAPEUTYCZNA",
    "SESJA_PSYCHOTERAPEUTYCZNA_GRUPOWA",
    "KONSULTACJA_SPECJALISTYCZNA",
    "BADANIA_LABORATORYJNE",
    "BADANIE_OBRAZOWE",
    "SUPERWIZJA",
    "KONSYLIUM",
    "ZAKONCZENIE_PROGRAMU",
    "BADANIA_GENETYCZNE",
}

FORBIDDEN_BLOCKS = {
    "RAPORT_KONCOWY",
    "DIAGNOSTYKA_PSYCHOLOGICZNA",
    "WIZYTA_PSYCHIATRYCZNA",
    "PSYCHOTERAPIA",
    "BADANIE_LAB",
    "BADANIE_GENETYCZNE",
    "ZAMKNIECIE_PROGRAMU",
}

FORBIDDEN_TYPES = {"SESJA", "DOKUMENT", "RAPORT"}
ALLOWED_TYPES = {
    "PKK",
    "WIZYTA",
    "KONSULTACJA",
    "BADANIE_LAB",
    "BADANIE_GEN",
    "BADANIE_OBRAZOWE",
    "SUPERWIZJA",
    "KONSYLIUM",
    "ZAKONCZENIE",
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
        r"\s*'(?P<ikona>[^']*)'\s*,\s*'(?P<kolor>#[0-9A-Fa-f]{6})'\s*,"
        r"\s*(?P<wymaga>[01])\s*,\s*(?P<obowiazkowy>[01])\s*,"
        r"\s*(?P<kolejnosc>[0-9]+)\s*\)",
        re.MULTILINE,
    )
    return {
        match.group("kod"): match.groupdict()
        for match in pattern.finditer(text)
    }


def test_seed_blocks():
    text = SEED_PATH.read_text(encoding="utf-8")
    blocks = _extract_seed_blocks()

    missing = EXPECTED_BLOCKS - set(blocks)
    if missing:
        raise AssertionError(
            "Brakuje docelowych klocków w seedzie: "
            + ", ".join(sorted(missing))
        )

    forbidden = FORBIDDEN_BLOCKS & set(blocks)
    if forbidden:
        raise AssertionError(
            "Usunięte klocki nadal występują w seedzie: "
            + ", ".join(sorted(forbidden))
        )

    for code in EXPECTED_BLOCKS:
        block = blocks[code]
        if _has_polish_characters(code):
            raise AssertionError(f"Kod klocka zawiera polskie znaki: {code}")
        if block["typ"] not in ALLOWED_TYPES:
            raise AssertionError(
                f"Klocek {code} ma nieoczekiwany typ: {block['typ']}"
            )

    for type_code in FORBIDDEN_TYPES:
        if re.search(rf"\('{type_code}'\s*,", text):
            raise AssertionError(f"Usunięty typ nadal występuje: {type_code}")

    if "pk_grupy_klockow" in text or "grupa_id" in text:
        raise AssertionError("Seed nie może zawierać mechanizmu grup klocków.")

    print("Seed PostgreSQL - docelowa biblioteka klocków: OK")
    print("Seed PostgreSQL - usunięte klocki i typy nie występują: OK")
    print("Seed PostgreSQL - typ klocka jest jedyną klasyfikacją: OK")


def test_schema_has_no_block_groups():
    text = (
        SCHEMA_PATH.read_text(encoding="utf-8")
        + "\n"
        + INDEX_PATH.read_text(encoding="utf-8")
    )
    forbidden_tokens = (
        "pk_grupy_klockow",
        "grupa_id",
        "idx_pk_klocki_grupa",
    )
    found = [token for token in forbidden_tokens if token in text]
    if found:
        raise AssertionError(
            "Schemat/indeksy nadal zawierają grupy klocków: "
            + ", ".join(found)
        )
    print("Schemat PostgreSQL - brak mechanizmu grup klocków: OK")


def test_live_postgres(dsn):
    from app.repositories.db_connection import DatabaseSettings, create_connection

    connection = create_connection(
        DatabaseSettings(engine="postgres", postgres_dsn=dsn)
    )
    try:
        rows = connection.execute(
            """
            SELECT k.kod, typ.kod AS typ_kod
            FROM pk_klocki k
            JOIN pk_typy_elementow typ
                ON typ.typ_id = k.typ_elementu_id
            WHERE k.czy_aktywny = 1
            """
        ).fetchall()
        found = {row["kod"] for row in rows}
        missing = EXPECTED_BLOCKS - found
        if missing:
            raise AssertionError(
                "Brakuje aktywnych klocków w PostgreSQL: "
                + ", ".join(sorted(missing))
            )

        forbidden_blocks = connection.execute(
            """
            SELECT kod
            FROM pk_klocki
            WHERE kod IN (
                'RAPORT_KONCOWY',
                'DIAGNOSTYKA_PSYCHOLOGICZNA',
                'WIZYTA_PSYCHIATRYCZNA',
                'PSYCHOTERAPIA'
            )
            """
        ).fetchall()
        if forbidden_blocks:
            raise AssertionError(
                "Usunięte klocki nadal istnieją w PostgreSQL: "
                + ", ".join(row["kod"] for row in forbidden_blocks)
            )

        forbidden_types = connection.execute(
            """
            SELECT kod
            FROM pk_typy_elementow
            WHERE kod IN ('SESJA', 'DOKUMENT', 'RAPORT')
            """
        ).fetchall()
        if forbidden_types:
            raise AssertionError(
                "Usunięte typy nadal istnieją w PostgreSQL: "
                + ", ".join(row["kod"] for row in forbidden_types)
            )
    finally:
        connection.close()
    print("PostgreSQL - biblioteka klocków: OK")


def main():
    test_seed_blocks()
    test_schema_has_no_block_groups()
    dsn = os.environ.get("KOMPAS_TEST_POSTGRES_DSN", "").strip()
    if dsn:
        test_live_postgres(dsn)
    else:
        print(
            "Test PostgreSQL pominięty. Ustaw KOMPAS_TEST_POSTGRES_DSN, "
            "aby sprawdzić żywą bazę."
        )


if __name__ == "__main__":
    main()
