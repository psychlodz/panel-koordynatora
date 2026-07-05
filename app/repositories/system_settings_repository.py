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
    if connection.engine == "sqlite":
        row = connection.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table'
              AND name = ?
            """,
            (table_name,),
        ).fetchone()
    else:
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
                SELECT typ_id, kod, nazwa
                FROM pk_typy_elementow
                ORDER BY nazwa COLLATE NOCASE, kod
                """
            ).fetchall()
        ]
        blocks = [
            dict(row)
            for row in connection.execute(
                """
                SELECT
                    klocek_id,
                    kod,
                    nazwa,
                    typ,
                    opis,
                    czy_aktywny
                FROM pk_klocki
                ORDER BY czy_aktywny DESC,
                         typ COLLATE NOCASE,
                         nazwa COLLATE NOCASE
                """
            ).fetchall()
        ]
        optional_tables = {
            key: _table_exists(connection, table_name)
            for key, table_name in OPTIONAL_DICTIONARY_TABLES.items()
        }
    return {
        "element_types": element_types,
        "blocks": blocks,
        "optional_tables": optional_tables,
    }


__all__ = ["get_business_dictionaries"]
