from contextlib import closing

from app.repositories.db_connection import (
    create_connection,
    initialize_database,
)


def _required_text(value, field_name):
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"Pole {field_name} jest wymagane")
    return text


def list_mapping_blocks(only_active=True) -> list[dict]:
    initialize_database()
    condition = "WHERE k.czy_aktywny = 1" if only_active else ""
    with closing(create_connection()) as connection:
        rows = connection.execute(
            f"""
            SELECT
                k.klocek_id,
                k.kod,
                k.nazwa,
                k.ikona,
                k.kolor,
                k.kolor_tekstu,
                grupa.kod AS grupa_kod,
                grupa.nazwa AS grupa_nazwa,
                COUNT(m.mapowanie_id) AS liczba_mapowan
            FROM pk_klocki k
            JOIN pk_grupy_klockow grupa
                ON grupa.grupa_id = k.grupa_id
            LEFT JOIN pk_mapowanie_wizyt m
                ON m.klocek_id = k.klocek_id
               AND m.czy_aktywne = 1
            {condition}
            GROUP BY
                k.klocek_id, k.kod, k.nazwa, k.ikona,
                k.kolor, k.kolor_tekstu,
                grupa.kod, grupa.nazwa, grupa.kolejnosc,
                k.kolejnosc
            ORDER BY grupa.kolejnosc, k.kolejnosc, k.nazwa
            """
        ).fetchall()
    return [dict(row) for row in rows]


def list_visit_mappings(
    klocek_id=None,
    only_active=True,
) -> list[dict]:
    initialize_database()
    conditions = []
    parameters = []
    if klocek_id is not None:
        conditions.append("m.klocek_id = ?")
        parameters.append(int(klocek_id))
    if only_active:
        conditions.append("m.czy_aktywne = 1")
    where_clause = (
        "WHERE " + " AND ".join(conditions)
        if conditions
        else ""
    )
    with closing(create_connection()) as connection:
        rows = connection.execute(
            f"""
            SELECT
                m.mapowanie_id,
                m.klocek_id,
                k.kod AS klocek_kod,
                k.nazwa AS klocek_nazwa,
                r.rodzaj_wizyty_id,
                r.parametr_kod,
                r.parametr_nazwa,
                r.parametr_nazwa AS parametr_nazwa_cache,
                r.czy_aktualny_eskulap,
                r.czy_aktywny_kompas,
                m.czy_aktywne,
                m.czy_aktywne AS czy_aktywny,
                m.created_at,
                m.updated_at
            FROM pk_mapowanie_wizyt m
            JOIN pk_klocki k ON k.klocek_id = m.klocek_id
            JOIN pk_rodzaje_wizyt_eskulap r
                ON r.rodzaj_wizyty_id = m.rodzaj_wizyty_id
            {where_clause}
            ORDER BY k.nazwa, r.parametr_nazwa, r.parametr_kod
            """,
            tuple(parameters),
        ).fetchall()
    return [dict(row) for row in rows]


def _ensure_visit_type(connection, parametr_kod, parametr_nazwa=None):
    code = _required_text(parametr_kod, "parametr_kod").upper()
    name = str(parametr_nazwa or "").strip() or code
    row = connection.execute(
        """
        SELECT rodzaj_wizyty_id
        FROM pk_rodzaje_wizyt_eskulap
        WHERE UPPER(parametr_kod) = ?
        """,
        (code,),
    ).fetchone()
    if row is not None:
        return int(row["rodzaj_wizyty_id"])

    cursor = connection.execute(
        """
        INSERT INTO pk_rodzaje_wizyt_eskulap(
            parametr_kod,
            parametr_nazwa,
            czy_aktualny_eskulap,
            czy_aktywny_kompas
        )
        VALUES (?, ?, 0, 1)
        """,
        (code, name),
    )
    return int(cursor.lastrowid)


def assign_visit_parameter(
    klocek_id,
    parametr_kod,
    parametr_nazwa=None,
) -> int:
    code = _required_text(parametr_kod, "parametr_kod").upper()
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            block = connection.execute(
                """
                SELECT klocek_id
                FROM pk_klocki
                WHERE klocek_id = ?
                  AND czy_aktywny = 1
                """,
                (int(klocek_id),),
            ).fetchone()
            if block is None:
                raise ValueError("Wybrany klocek nie istnieje lub jest nieaktywny")

            visit_type_id = _ensure_visit_type(
                connection,
                code,
                parametr_nazwa,
            )

            connection.execute(
                """
                UPDATE pk_mapowanie_wizyt
                SET czy_aktywne = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE rodzaj_wizyty_id = ?
                  AND czy_aktywne = 1
                  AND klocek_id <> ?
                """,
                (visit_type_id, int(klocek_id)),
            )

            existing = connection.execute(
                """
                SELECT mapowanie_id
                FROM pk_mapowanie_wizyt
                WHERE klocek_id = ?
                  AND rodzaj_wizyty_id = ?
                """,
                (int(klocek_id), visit_type_id),
            ).fetchone()
            if existing is not None:
                connection.execute(
                    """
                    UPDATE pk_mapowanie_wizyt
                    SET czy_aktywne = 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE mapowanie_id = ?
                    """,
                    (existing["mapowanie_id"],),
                )
                return int(existing["mapowanie_id"])

            cursor = connection.execute(
                """
                INSERT INTO pk_mapowanie_wizyt(
                    klocek_id,
                    rodzaj_wizyty_id,
                    czy_aktywne
                )
                VALUES (?, ?, 1)
                """,
                (int(klocek_id), visit_type_id),
            )
            return int(cursor.lastrowid)


def delete_visit_mapping(mapowanie_id) -> None:
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            cursor = connection.execute(
                """
                DELETE FROM pk_mapowanie_wizyt
                WHERE mapowanie_id = ?
                """,
                (int(mapowanie_id),),
            )
            if cursor.rowcount == 0:
                raise ValueError("Nie znaleziono wybranego mapowania")


def get_active_parameter_codes_for_block(klocek_kod) -> tuple[str, ...]:
    code = _required_text(klocek_kod, "klocek_kod").upper()
    initialize_database()
    with closing(create_connection()) as connection:
        rows = connection.execute(
            """
            SELECT r.parametr_kod
            FROM pk_mapowanie_wizyt m
            JOIN pk_klocki k ON k.klocek_id = m.klocek_id
            JOIN pk_rodzaje_wizyt_eskulap r
                ON r.rodzaj_wizyty_id = m.rodzaj_wizyty_id
            WHERE UPPER(k.kod) = ?
              AND k.czy_aktywny = 1
              AND m.czy_aktywne = 1
              AND r.czy_aktywny_kompas = 1
            ORDER BY r.parametr_kod
            """,
            (code,),
        ).fetchall()
    return tuple(str(row["parametr_kod"]).strip().upper() for row in rows)


def get_block_for_visit_parameter(parametr_kod):
    code = _required_text(parametr_kod, "parametr_kod").upper()
    initialize_database()
    with closing(create_connection()) as connection:
        row = connection.execute(
            """
            SELECT
                k.klocek_id,
                k.kod,
                k.nazwa,
                k.kolor,
                k.kolor_tekstu,
                m.mapowanie_id,
                r.rodzaj_wizyty_id,
                r.parametr_kod,
                r.parametr_nazwa,
                r.parametr_nazwa AS parametr_nazwa_cache
            FROM pk_mapowanie_wizyt m
            JOIN pk_klocki k ON k.klocek_id = m.klocek_id
            JOIN pk_rodzaje_wizyt_eskulap r
                ON r.rodzaj_wizyty_id = m.rodzaj_wizyty_id
            WHERE UPPER(r.parametr_kod) = ?
              AND m.czy_aktywne = 1
              AND k.czy_aktywny = 1
              AND r.czy_aktywny_kompas = 1
            """,
            (code,),
        ).fetchone()
    return dict(row) if row is not None else None


__all__ = [
    "assign_visit_parameter",
    "delete_visit_mapping",
    "get_active_parameter_codes_for_block",
    "get_block_for_visit_parameter",
    "list_mapping_blocks",
    "list_visit_mappings",
]
