from contextlib import closing

from local_db import create_local_connection, initialize_local_db


def _required_text(value, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"Pole {field_name} jest wymagane")
    return text


def _optional_text(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _nonnegative_int(value, field_name: str, allow_none=False):
    if value is None or value == "":
        if allow_none:
            return None
        value = 0
    number = int(value)
    if number < 0:
        raise ValueError(f"Pole {field_name} nie może być ujemne")
    return number


def _element_values(
    klocek_id,
    lp,
    nazwa_w_sciezce,
    min_liczba,
    max_liczba,
    czy_obowiazkowy,
    czy_wymaga_zlecenia,
    termin_liczba,
    termin_jednostka,
    termin_od,
    warunek_aktywacji,
    opis_organizacyjny,
):
    position = int(lp)
    if position < 1:
        raise ValueError("Pole lp musi być większe od zera")
    minimum = _nonnegative_int(min_liczba, "min_liczba")
    maximum = _nonnegative_int(max_liczba, "max_liczba", allow_none=True)
    if maximum is not None and maximum < minimum:
        raise ValueError("max_liczba nie może być mniejsza od min_liczba")
    deadline = _nonnegative_int(
        termin_liczba, "termin_liczba", allow_none=True
    )
    return (
        int(klocek_id),
        position,
        _required_text(nazwa_w_sciezce, "nazwa_w_sciezce"),
        minimum,
        maximum,
        1 if czy_obowiazkowy else 0,
        1 if czy_wymaga_zlecenia else 0,
        deadline,
        _optional_text(termin_jednostka),
        _optional_text(termin_od),
        _optional_text(warunek_aktywacji),
        _optional_text(opis_organizacyjny),
    )


def list_pathways(program_id) -> list[dict]:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        rows = connection.execute(
            """
            SELECT
                sciezka_id,
                program_id,
                kod,
                nazwa,
                opis,
                czy_aktywna,
                created_at,
                updated_at
            FROM pk_sciezki
            WHERE program_id = ?
            ORDER BY czy_aktywna DESC, kod COLLATE NOCASE
            """,
            (program_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_pathway(sciezka_id):
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        row = connection.execute(
            """
            SELECT
                sciezka_id,
                program_id,
                kod,
                nazwa,
                opis,
                czy_aktywna,
                created_at,
                updated_at
            FROM pk_sciezki
            WHERE sciezka_id = ?
            """,
            (sciezka_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def create_pathway(program_id, kod, nazwa, opis=None) -> int:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO pk_sciezki(program_id, kod, nazwa, opis)
                VALUES (?, ?, ?, ?)
                """,
                (
                    program_id,
                    _required_text(kod, "kod"),
                    _required_text(nazwa, "nazwa"),
                    _optional_text(opis),
                ),
            )
            sciezka_id = cursor.lastrowid
    return int(sciezka_id)


def update_pathway(
    sciezka_id,
    kod,
    nazwa,
    opis=None,
    czy_aktywna=1,
) -> int:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        with connection:
            cursor = connection.execute(
                """
                UPDATE pk_sciezki
                SET kod = ?,
                    nazwa = ?,
                    opis = ?,
                    czy_aktywna = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE sciezka_id = ?
                """,
                (
                    _required_text(kod, "kod"),
                    _required_text(nazwa, "nazwa"),
                    _optional_text(opis),
                    1 if czy_aktywna else 0,
                    sciezka_id,
                ),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Nie znaleziono ścieżki o ID {sciezka_id}")
    return int(sciezka_id)


def list_pathway_elements(sciezka_id) -> list[dict]:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        rows = connection.execute(
            """
            SELECT
                e.element_id,
                e.sciezka_id,
                e.klocek_id,
                e.lp,
                e.nazwa_w_sciezce,
                e.min_liczba,
                e.max_liczba,
                e.czy_obowiazkowy,
                e.czy_wymaga_zlecenia,
                e.termin_liczba,
                e.termin_jednostka,
                e.termin_od,
                e.warunek_aktywacji,
                e.opis_organizacyjny,
                e.czy_aktywny,
                e.created_at,
                e.updated_at,
                k.kod AS klocek_kod,
                k.nazwa AS klocek_nazwa,
                k.typ AS klocek_typ
            FROM pk_sciezka_elementy e
            JOIN pk_klocki k ON k.klocek_id = e.klocek_id
            WHERE e.sciezka_id = ?
            ORDER BY e.lp, e.element_id
            """,
            (sciezka_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_blocks() -> list[dict]:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        rows = connection.execute(
            """
            SELECT
                klocek_id,
                kod,
                nazwa,
                typ,
                opis,
                ikona,
                czy_aktywny
            FROM pk_klocki
            WHERE czy_aktywny = 1
            ORDER BY typ COLLATE NOCASE, nazwa COLLATE NOCASE
            """
        ).fetchall()
    return [dict(row) for row in rows]


def add_element_to_pathway(
    sciezka_id,
    klocek_id,
    lp,
    nazwa_w_sciezce,
    min_liczba=0,
    max_liczba=None,
    czy_obowiazkowy=0,
    czy_wymaga_zlecenia=0,
    termin_liczba=None,
    termin_jednostka=None,
    termin_od=None,
    warunek_aktywacji=None,
    opis_organizacyjny=None,
) -> int:
    values = _element_values(
        klocek_id,
        lp,
        nazwa_w_sciezce,
        min_liczba,
        max_liczba,
        czy_obowiazkowy,
        czy_wymaga_zlecenia,
        termin_liczba,
        termin_jednostka,
        termin_od,
        warunek_aktywacji,
        opis_organizacyjny,
    )
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO pk_sciezka_elementy(
                    sciezka_id,
                    klocek_id,
                    lp,
                    nazwa_w_sciezce,
                    min_liczba,
                    max_liczba,
                    czy_obowiazkowy,
                    czy_wymaga_zlecenia,
                    termin_liczba,
                    termin_jednostka,
                    termin_od,
                    warunek_aktywacji,
                    opis_organizacyjny
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (sciezka_id, *values),
            )
            element_id = cursor.lastrowid
    return int(element_id)


def update_pathway_element(
    element_id,
    klocek_id,
    lp,
    nazwa_w_sciezce,
    min_liczba=0,
    max_liczba=None,
    czy_obowiazkowy=0,
    czy_wymaga_zlecenia=0,
    termin_liczba=None,
    termin_jednostka=None,
    termin_od=None,
    warunek_aktywacji=None,
    opis_organizacyjny=None,
) -> int:
    values = _element_values(
        klocek_id,
        lp,
        nazwa_w_sciezce,
        min_liczba,
        max_liczba,
        czy_obowiazkowy,
        czy_wymaga_zlecenia,
        termin_liczba,
        termin_jednostka,
        termin_od,
        warunek_aktywacji,
        opis_organizacyjny,
    )
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        with connection:
            cursor = connection.execute(
                """
                UPDATE pk_sciezka_elementy
                SET klocek_id = ?,
                    lp = ?,
                    nazwa_w_sciezce = ?,
                    min_liczba = ?,
                    max_liczba = ?,
                    czy_obowiazkowy = ?,
                    czy_wymaga_zlecenia = ?,
                    termin_liczba = ?,
                    termin_jednostka = ?,
                    termin_od = ?,
                    warunek_aktywacji = ?,
                    opis_organizacyjny = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE element_id = ?
                """,
                (*values, element_id),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Nie znaleziono elementu o ID {element_id}")
    return int(element_id)


def delete_pathway_element(element_id) -> None:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        with connection:
            cursor = connection.execute(
                """
                DELETE FROM pk_sciezka_elementy
                WHERE element_id = ?
                """,
                (element_id,),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Nie znaleziono elementu o ID {element_id}")
