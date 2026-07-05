from contextlib import closing

from app.repositories.db_connection import (
    create_connection,
    initialize_database,
)


OPTIONAL_DICTIONARY_TABLES = {
    "block_groups": "pk_grupy_klockow",
    "time_units": "pk_jednostki_czasu",
}


def _table_exists(connection, table_name):
    row = connection.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def get_business_dictionaries():
    """Zwraca słowniki KOMPAS wyłącznie do prezentacji."""
    initialize_database()
    with closing(create_connection()) as connection:
        element_types = [
            dict(row)
            for row in connection.execute(
                """
                SELECT
                    typ_id, kod, nazwa, opis, kolejnosc,
                    czy_aktywny, czy_systemowy, ikona, kolor
                FROM pk_typy_elementow
                ORDER BY kolejnosc, nazwa COLLATE NOCASE, kod
                """
            ).fetchall()
        ]
        blocks = [
            dict(row)
            for row in connection.execute(
                """
                SELECT
                    k.klocek_id,
                    k.kod,
                    k.nazwa,
                    typ.kod AS typ,
                    typ.nazwa AS typ_nazwa,
                    grupa.kod AS grupa,
                    grupa.nazwa AS grupa_nazwa,
                    k.opis,
                    k.ikona,
                    k.kolor,
                    k.kolor_tekstu,
                    k.czy_aktywny,
                    k.czy_systemowy,
                    k.kolejnosc
                FROM pk_klocki k
                JOIN pk_typy_elementow typ
                    ON typ.typ_id = k.typ_elementu_id
                JOIN pk_grupy_klockow grupa
                    ON grupa.grupa_id = k.grupa_id
                ORDER BY k.czy_aktywny DESC,
                         grupa.kolejnosc,
                         k.kolejnosc,
                         k.nazwa COLLATE NOCASE
                """
            ).fetchall()
        ]
        optional_tables = {
            key: _table_exists(connection, table_name)
            for key, table_name in OPTIONAL_DICTIONARY_TABLES.items()
        }
        block_groups = [
            dict(row)
            for row in connection.execute(
                """
                SELECT
                    grupa_id, kod, nazwa, opis, kolejnosc,
                    czy_aktywny, czy_systemowy, ikona, kolor
                FROM pk_grupy_klockow
                ORDER BY kolejnosc, nazwa COLLATE NOCASE
                """
            ).fetchall()
        ]
        time_units = [
            dict(row)
            for row in connection.execute(
                """
                SELECT
                    jednostka_czasu_id, kod, nazwa, opis,
                    rodzaj_obliczenia, mnoznik, kolejnosc,
                    czy_aktywny, czy_systemowy
                FROM pk_jednostki_czasu
                ORDER BY kolejnosc, nazwa COLLATE NOCASE
                """
            ).fetchall()
        ]
    return {
        "element_types": element_types,
        "blocks": blocks,
        "block_groups": block_groups,
        "time_units": time_units,
        "optional_tables": optional_tables,
    }


__all__ = ["get_business_dictionaries"]
