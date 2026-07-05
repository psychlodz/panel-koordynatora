import sqlite3
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


EXPECTED_ELEMENT_TYPES = {
    "PKK",
    "WIZYTA",
    "SESJA",
    "KONSULTACJA",
    "BADANIE_LAB",
    "BADANIE_GEN",
    "BADANIE_OBRAZOWE",
    "KONSYLIUM",
    "DOKUMENT",
    "RAPORT",
    "ZAKONCZENIE",
}

EXPECTED_BLOCK_GROUPS = {
    "KWALIFIKACJA",
    "WIZYTY",
    "KONSULTACJE",
    "BADANIA_LAB",
    "BADANIA_OBRAZOWE",
    "DIAGNOSTYKA",
    "PSYCHOTERAPIA",
    "DOKUMENTACJA",
    "RAPORTY",
    "ZAKONCZENIE_PROGRAMU",
}

EXPECTED_TIME_UNITS = {
    "DZIEN": ("DNI", 1),
    "TYDZIEN": ("DNI", 7),
    "MIESIAC": ("MIESIACE", 1),
}


def _sqlite_connection(database_path):
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _codes(connection, table_name):
    return {
        row[0]
        for row in connection.execute(
            f"SELECT kod FROM {table_name}"
        ).fetchall()
    }


def _verify(connection):
    assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    print("Integralność kluczy obcych: OK")

    assert EXPECTED_ELEMENT_TYPES <= _codes(
        connection, "pk_typy_elementow"
    )
    print("Typy elementów procesu: OK")

    assert EXPECTED_BLOCK_GROUPS <= _codes(
        connection, "pk_grupy_klockow"
    )
    print("Grupy klocków: OK")

    time_units = {
        row[0]: (row[1], row[2])
        for row in connection.execute(
            """
            SELECT kod, rodzaj_obliczenia, mnoznik
            FROM pk_jednostki_czasu
            """
        ).fetchall()
    }
    assert all(
        time_units.get(code) == definition
        for code, definition in EXPECTED_TIME_UNITS.items()
    )
    print("Jednostki czasu: OK")

    columns = {
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(pk_klocki)"
        ).fetchall()
    }
    assert "typ" not in columns
    assert {
        "typ_elementu_id",
        "grupa_id",
        "domyslna_jednostka_czasu_id",
    } <= columns

    blocks_without_dictionary = connection.execute(
        """
        SELECT COUNT(*)
        FROM pk_klocki k
        LEFT JOIN pk_typy_elementow typ
            ON typ.typ_id = k.typ_elementu_id
        LEFT JOIN pk_grupy_klockow grupa
            ON grupa.grupa_id = k.grupa_id
        WHERE typ.typ_id IS NULL
           OR grupa.grupa_id IS NULL
        """
    ).fetchone()[0]
    assert blocks_without_dictionary == 0
    print("Powiązania klocków z typem i grupą: OK")

    pkk_blocks = {
        row[0]: (row[1], row[2], row[3])
        for row in connection.execute(
            """
            SELECT k.kod, typ.kod, grupa.kod, k.opis
            FROM pk_klocki k
            JOIN pk_typy_elementow typ
                ON typ.typ_id = k.typ_elementu_id
            JOIN pk_grupy_klockow grupa
                ON grupa.grupa_id = k.grupa_id
            WHERE k.kod IN ('PKK_KWAL', 'PKK_WIZ')
            """
        ).fetchall()
    }
    assert pkk_blocks["PKK_KWAL"][:2] == ("PKK", "KWALIFIKACJA")
    assert "F18" in pkk_blocks["PKK_KWAL"][2]
    assert pkk_blocks["PKK_WIZ"][:2] == ("PKK", "WIZYTY")
    print("Klocki PKK_KWAL i PKK_WIZ: OK")

    active_general_pkk = connection.execute(
        """
        SELECT COUNT(*)
        FROM pk_klocki
        WHERE kod = 'PKK'
          AND czy_aktywny = 1
        """
    ).fetchone()[0]
    assert active_general_pkk == 0
    print("Brak aktywnego ogólnego klocka PKK: OK")


def _verify_repository(database_path):
    from app.repositories import pathway_repository

    pathway_repository.initialize_local_db = lambda: database_path
    pathway_repository.create_local_connection = (
        lambda: _sqlite_connection(database_path)
    )
    blocks = pathway_repository.list_blocks()
    assert blocks
    assert all(
        block["typ"] and block["grupa"] and block["grupa_nazwa"]
        for block in blocks
    )
    assert blocks[0]["kod"] == "PKK_KWAL"
    print("Repozytorium biblioteki i sortowanie: OK")


def main():
    with tempfile.TemporaryDirectory(
        prefix="kompas_business_dictionaries_"
    ) as temp_dir:
        database_path = Path(temp_dir) / "kompas_test.db"
        connection = _sqlite_connection(database_path)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            for script_name in (
                "schema.sql",
                "seed.sql",
                "migrations.sql",
            ):
                connection.executescript(
                    (PROJECT_ROOT / "db" / script_name).read_text(
                        encoding="utf-8"
                    )
                )
            _verify(connection)
        finally:
            connection.close()
        _verify_repository(database_path)

    print("Test słowników biznesowych zakończony powodzeniem.")


if __name__ == "__main__":
    main()
