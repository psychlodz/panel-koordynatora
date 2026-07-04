from contextlib import closing

from app.repositories.db_connection import (
    create_connection as create_local_connection,
    initialize_database as initialize_local_db,
)


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
                k.typ AS klocek_typ,
                k.ikona AS klocek_ikona
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


def _element_row(connection, element_id):
    return connection.execute(
        """
        SELECT element_id, sciezka_id
        FROM pk_sciezka_elementy
        WHERE element_id = ?
        """,
        (element_id,),
    ).fetchone()


def _has_completed_task(connection, element_id) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM pk_zadania
        WHERE element_id = ?
          AND UPPER(TRIM(status)) = 'ZREALIZOWANO'
        LIMIT 1
        """,
        (element_id,),
    ).fetchone()
    return row is not None


def _ordered_element_ids(connection, sciezka_id):
    rows = connection.execute(
        """
        SELECT element_id
        FROM pk_sciezka_elementy
        WHERE sciezka_id = ?
        ORDER BY lp, element_id
        """,
        (sciezka_id,),
    ).fetchall()
    return [int(row["element_id"]) for row in rows]


def _reorder_elements_in_connection(
    connection,
    sciezka_id,
    ordered_element_ids,
):
    ordered_ids = [int(element_id) for element_id in ordered_element_ids]
    if len(ordered_ids) != len(set(ordered_ids)):
        raise ValueError("Lista elementów zawiera powtórzone identyfikatory")

    current_ids = _ordered_element_ids(connection, sciezka_id)
    if set(ordered_ids) != set(current_ids) or len(ordered_ids) != len(
        current_ids
    ):
        raise ValueError(
            "Nowa kolejność musi zawierać wszystkie elementy jednej ścieżki"
        )

    # Wartości ujemne usuwają chwilowe kolizje z UNIQUE(sciezka_id, lp).
    connection.execute(
        """
        UPDATE pk_sciezka_elementy
        SET lp = -element_id
        WHERE sciezka_id = ?
        """,
        (sciezka_id,),
    )
    for position, element_id in enumerate(ordered_ids, start=1):
        connection.execute(
            """
            UPDATE pk_sciezka_elementy
            SET lp = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE sciezka_id = ?
              AND element_id = ?
            """,
            (position, sciezka_id, element_id),
        )


def reorder_elements(sciezka_id, ordered_element_ids) -> None:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            pathway = connection.execute(
                """
                SELECT 1
                FROM pk_sciezki
                WHERE sciezka_id = ?
                """,
                (sciezka_id,),
            ).fetchone()
            if pathway is None:
                raise ValueError(f"Nie znaleziono ścieżki o ID {sciezka_id}")
            _reorder_elements_in_connection(
                connection,
                sciezka_id,
                ordered_element_ids,
            )


def can_delete_element(element_id) -> bool:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        if _element_row(connection, element_id) is None:
            return False
        return not _has_completed_task(connection, element_id)


def can_insert_before(element_id) -> bool:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        if _element_row(connection, element_id) is None:
            return False
        return not _has_completed_task(connection, element_id)


def get_element_link_counts(element_id) -> dict:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        if _element_row(connection, element_id) is None:
            raise ValueError(f"Nie znaleziono elementu o ID {element_id}")
        dependencies = connection.execute(
            """
            SELECT COUNT(*)
            FROM pk_sciezka_zaleznosci
            WHERE element_od_id = ?
               OR element_do_id = ?
            """,
            (element_id, element_id),
        ).fetchone()[0]
        triggers = connection.execute(
            """
            SELECT COUNT(*)
            FROM pk_wyzwalacze
            WHERE element_id = ?
               OR trigger_element_id = ?
            """,
            (element_id, element_id),
        ).fetchone()[0]
    return {
        "dependencies": int(dependencies),
        "triggers": int(triggers),
    }


def delete_element_safe(element_id) -> None:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            element = _element_row(connection, element_id)
            if element is None:
                raise ValueError(f"Nie znaleziono elementu o ID {element_id}")
            if _has_completed_task(connection, element_id):
                raise ValueError(
                    "Nie można usunąć elementu, ponieważ istnieje "
                    "powiązane zadanie o statusie ZREALIZOWANO."
                )

            sciezka_id = int(element["sciezka_id"])
            connection.execute(
                """
                DELETE FROM pk_sciezka_zaleznosci
                WHERE element_od_id = ?
                   OR element_do_id = ?
                """,
                (element_id, element_id),
            )
            connection.execute(
                """
                DELETE FROM pk_wyzwalacze
                WHERE element_id = ?
                   OR trigger_element_id = ?
                """,
                (element_id, element_id),
            )
            connection.execute(
                """
                UPDATE pk_zadania
                SET element_id = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE element_id = ?
                """,
                (element_id,),
            )
            connection.execute(
                """
                DELETE FROM pk_sciezka_elementy
                WHERE element_id = ?
                """,
                (element_id,),
            )
            _reorder_elements_in_connection(
                connection,
                sciezka_id,
                _ordered_element_ids(connection, sciezka_id),
            )


def add_element_at_position(
    sciezka_id,
    klocek_id,
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
    before_element_id=None,
    position=None,
    lp=None,
) -> int:
    if lp is not None:
        if position is not None:
            raise ValueError(
                "Podaj tylko jeden parametr pozycji: lp lub position"
            )
        position = lp
    if before_element_id is not None and position is not None:
        raise ValueError(
            "Podaj element docelowy albo numer pozycji, ale nie oba naraz"
        )

    values = list(
        _element_values(
            klocek_id,
            1,
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
    )
    values[1] = 0

    initialize_local_db()
    with closing(create_local_connection()) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            ordered_ids = _ordered_element_ids(connection, sciezka_id)
            if position is not None:
                position = int(position)
                if position < 1 or position > len(ordered_ids) + 1:
                    raise ValueError("Pozycja elementu jest poza zakresem")
                if position <= len(ordered_ids):
                    before_element_id = ordered_ids[position - 1]
            if before_element_id is not None:
                before_element_id = int(before_element_id)
                if before_element_id not in ordered_ids:
                    raise ValueError(
                        "Wybrany element nie należy do wskazanej ścieżki"
                    )
                if _has_completed_task(connection, before_element_id):
                    raise ValueError(
                        "Nie można wstawić elementu przed wskazanym "
                        "elementem, ponieważ ma on zrealizowane zadanie."
                    )

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
            element_id = int(cursor.lastrowid)
            if before_element_id is None:
                ordered_ids.append(element_id)
            else:
                insert_at = ordered_ids.index(before_element_id)
                ordered_ids.insert(insert_at, element_id)
            _reorder_elements_in_connection(
                connection,
                sciezka_id,
                ordered_ids,
            )
    return element_id
