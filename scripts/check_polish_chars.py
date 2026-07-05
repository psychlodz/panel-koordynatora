import sys
from contextlib import closing
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.repositories.db_connection import (
    create_connection,
    initialize_database,
    load_database_settings,
)


SUSPICIOUS_CHARACTERS = ("Å", "Ä", "Ã", "Â")
TEXT_COLUMNS = {
    "pk_programy": (
        "program_id",
        ("kod", "nazwa", "wersja", "opis"),
    ),
    "pk_sciezki": (
        "sciezka_id",
        ("kod", "nazwa", "opis"),
    ),
    "pk_klocki": (
        "klocek_id",
        ("kod", "nazwa", "opis", "ikona", "kolor"),
    ),
    "pk_typy_elementow": (
        "typ_id",
        ("kod", "nazwa", "opis", "ikona", "kolor"),
    ),
    "pk_grupy_klockow": (
        "grupa_id",
        ("kod", "nazwa", "opis", "ikona", "kolor"),
    ),
    "pk_jednostki_czasu": (
        "jednostka_czasu_id",
        ("kod", "nazwa", "opis", "rodzaj_obliczenia"),
    ),
    "pk_sciezka_elementy": (
        "element_id",
        (
            "nazwa_w_sciezce",
            "termin_jednostka",
            "termin_od",
            "warunek_aktywacji",
            "opis_organizacyjny",
        ),
    ),
}


def contains_suspicious_characters(value):
    return isinstance(value, str) and any(
        character in value
        for character in SUSPICIOUS_CHARACTERS
    )


def table_exists(connection, table_name):
    return connection.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = ?
        """,
        (table_name,),
    ).fetchone() is not None


def database_encoding(connection):
    return connection.execute(
        """
        SELECT
            datname,
            pg_encoding_to_char(encoding) AS encoding,
            datcollate,
            datctype
        FROM pg_database
        WHERE datname = current_database()
        """
    ).fetchone()


def find_suspicious_records(connection):
    findings = []
    for table_name, (primary_key, columns) in TEXT_COLUMNS.items():
        if not table_exists(connection, table_name):
            continue
        selected_columns = ", ".join((primary_key, *columns))
        rows = connection.execute(
            f"SELECT {selected_columns} FROM {table_name}"
        ).fetchall()
        for row in rows:
            for column_name in columns:
                value = row[column_name]
                if contains_suspicious_characters(value):
                    findings.append(
                        {
                            "table": table_name,
                            "primary_key": primary_key,
                            "record_id": row[primary_key],
                            "column": column_name,
                            "value": value,
                        }
                    )
    return findings


def main():
    try:
        settings = load_database_settings()
        if settings.engine != "postgres":
            raise RuntimeError(
                "Test wymaga konfiguracji engine=postgres."
            )
        initialize_database(settings)
        with closing(create_connection(settings)) as connection:
            encoding = database_encoding(connection)
            client_encoding = connection.execute(
                "SHOW client_encoding"
            ).fetchone()[0]
            findings = find_suspicious_records(connection)
    except Exception as exc:
        print(f"BŁĄD POŁĄCZENIA: {exc}", file=sys.stderr)
        return 2

    print(
        "Baza: "
        f"{encoding['datname']}, "
        f"encoding={encoding['encoding']}, "
        f"collate={encoding['datcollate']}, "
        f"ctype={encoding['datctype']}"
    )
    print(f"client_encoding={client_encoding}")

    errors = 0
    if str(encoding["encoding"]).upper() != "UTF8":
        print("BŁĄD: baza KOMPAS nie używa kodowania UTF8.")
        errors += 1
    if str(client_encoding).upper() != "UTF8":
        print("BŁĄD: połączenie nie używa client_encoding=UTF8.")
        errors += 1

    for finding in findings:
        print(
            "PODEJRZANY TEKST: "
            f"{finding['table']}.{finding['column']} "
            f"({finding['primary_key']}={finding['record_id']}): "
            f"{finding['value']!r}"
        )
    errors += len(findings)

    if errors:
        print(f"Wykryto problemów: {errors}")
        return 1
    print("Nie wykryto błędnie zakodowanych polskich znaków.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
