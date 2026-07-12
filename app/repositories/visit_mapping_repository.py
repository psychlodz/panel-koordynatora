from contextlib import closing

from app.repositories.db_connection import (
    create_connection,
    initialize_database,
)


class VisitTypeMappingConflict(ValueError):
    def __init__(self, conflicts):
        self.conflicts = conflicts
        first = conflicts[0] if conflicts else {}
        message = (
            "Rodzaj wizyty "
            f"{first.get('parametr_kod', '')} jest już przypisany do klocka "
            f"{first.get('klocek_kod', '')}."
        )
        super().__init__(message)


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
                typ.kod AS typ_kod,
                typ.nazwa AS typ_nazwa,
                COUNT(m.mapowanie_id) AS liczba_mapowan
            FROM pk_klocki k
            JOIN pk_typy_elementow typ
                ON typ.typ_id = k.typ_elementu_id
            LEFT JOIN pk_mapowanie_wizyt m
                ON m.klocek_id = k.klocek_id
               AND m.czy_aktywne = 1
            {condition}
            GROUP BY
                k.klocek_id, k.kod, k.nazwa, k.ikona,
                k.kolor, k.kolor_tekstu,
                typ.kod, typ.nazwa, typ.kolejnosc,
                k.kolejnosc
            ORDER BY typ.kolejnosc, k.kolejnosc, k.nazwa
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


def list_mappings_for_block(klocek_id, only_active=True) -> list[dict]:
    return list_visit_mappings(klocek_id=klocek_id, only_active=only_active)


def list_blocks_with_visit_types(only_active=True) -> list[dict]:
    return list_mapping_blocks(only_active=only_active)


def _placeholders(values):
    return ",".join("?" for _ in values)


def _validate_block(connection, klocek_id):
    block = connection.execute(
        """
        SELECT klocek_id, kod, nazwa
        FROM pk_klocki
        WHERE klocek_id = ?
          AND czy_aktywny = 1
        """,
        (int(klocek_id),),
    ).fetchone()
    if block is None:
        raise ValueError("Wybrany klocek nie istnieje lub jest nieaktywny")
    return block


def _validate_visit_type_ids(connection, visit_type_ids):
    ids = sorted({int(value) for value in (visit_type_ids or [])})
    if not ids:
        return []
    rows = connection.execute(
        f"""
        SELECT rodzaj_wizyty_id
        FROM pk_rodzaje_wizyt_eskulap
        WHERE rodzaj_wizyty_id IN ({_placeholders(ids)})
        """,
        tuple(ids),
    ).fetchall()
    existing = {int(row["rodzaj_wizyty_id"]) for row in rows}
    missing = sorted(set(ids) - existing)
    if missing:
        raise ValueError(
            "Nie znaleziono rodzajów wizyt: "
            + ", ".join(str(value) for value in missing)
        )
    return ids


def _active_conflicts(connection, klocek_id, visit_type_ids):
    ids = sorted({int(value) for value in (visit_type_ids or [])})
    if not ids:
        return []
    rows = connection.execute(
        f"""
        SELECT
            m.mapowanie_id,
            m.klocek_id,
            k.kod AS klocek_kod,
            k.nazwa AS klocek_nazwa,
            r.rodzaj_wizyty_id,
            r.parametr_kod,
            r.parametr_nazwa
        FROM pk_mapowanie_wizyt m
        JOIN pk_klocki k ON k.klocek_id = m.klocek_id
        JOIN pk_rodzaje_wizyt_eskulap r
            ON r.rodzaj_wizyty_id = m.rodzaj_wizyty_id
        WHERE m.rodzaj_wizyty_id IN ({_placeholders(ids)})
          AND m.czy_aktywne = 1
          AND m.klocek_id <> ?
        ORDER BY r.parametr_kod
        """,
        tuple(ids) + (int(klocek_id),),
    ).fetchall()
    return [dict(row) for row in rows]


def assign_visit_types(
    klocek_id,
    visit_type_ids,
    replace_conflicts=False,
) -> dict:
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            _validate_block(connection, klocek_id)
            selected_ids = _validate_visit_type_ids(connection, visit_type_ids)
            selected_set = set(selected_ids)

            conflicts = _active_conflicts(
                connection,
                klocek_id,
                selected_ids,
            )
            if conflicts and not replace_conflicts:
                raise VisitTypeMappingConflict(conflicts)
            removed = 0
            if conflicts:
                cursor = connection.execute(
                    f"""
                    UPDATE pk_mapowanie_wizyt
                    SET czy_aktywne = 0,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE mapowanie_id IN ({
                        _placeholders([row["mapowanie_id"] for row in conflicts])
                    })
                    """,
                    tuple(row["mapowanie_id"] for row in conflicts),
                )
                removed += int(cursor.rowcount or 0)

            current_rows = connection.execute(
                """
                SELECT mapowanie_id, rodzaj_wizyty_id
                FROM pk_mapowanie_wizyt
                WHERE klocek_id = ?
                  AND czy_aktywne = 1
                """,
                (int(klocek_id),),
            ).fetchall()
            current_ids = {
                int(row["rodzaj_wizyty_id"])
                for row in current_rows
            }
            to_remove = current_ids - selected_set
            if to_remove:
                cursor = connection.execute(
                    f"""
                    UPDATE pk_mapowanie_wizyt
                    SET czy_aktywne = 0,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE klocek_id = ?
                      AND czy_aktywne = 1
                      AND rodzaj_wizyty_id IN ({_placeholders(to_remove)})
                    """,
                    (int(klocek_id),) + tuple(sorted(to_remove)),
                )
                removed += int(cursor.rowcount or 0)

            added = 0
            for visit_type_id in selected_ids:
                existing = connection.execute(
                    """
                    SELECT mapowanie_id, czy_aktywne
                    FROM pk_mapowanie_wizyt
                    WHERE klocek_id = ?
                      AND rodzaj_wizyty_id = ?
                    """,
                    (int(klocek_id), int(visit_type_id)),
                ).fetchone()
                if existing is not None:
                    if int(existing["czy_aktywne"] or 0) == 0:
                        connection.execute(
                            """
                            UPDATE pk_mapowanie_wizyt
                            SET czy_aktywne = 1,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE mapowanie_id = ?
                            """,
                            (existing["mapowanie_id"],),
                        )
                        added += 1
                    continue

                connection.execute(
                    """
                    INSERT INTO pk_mapowanie_wizyt(
                        klocek_id,
                        rodzaj_wizyty_id,
                        czy_aktywne
                    )
                    VALUES (?, ?, 1)
                    """,
                    (int(klocek_id), int(visit_type_id)),
                )
                added += 1

            return {
                "added": added,
                "removed": removed,
                "conflicts_replaced": len(conflicts),
            }


def remove_mapping(mapowanie_id) -> None:
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            cursor = connection.execute(
                """
                UPDATE pk_mapowanie_wizyt
                SET czy_aktywne = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE mapowanie_id = ?
                  AND czy_aktywne = 1
                """,
                (int(mapowanie_id),),
            )
            if cursor.rowcount == 0:
                raise ValueError("Nie znaleziono aktywnego mapowania")


def remove_mappings(mapping_ids) -> int:
    ids = sorted({int(value) for value in (mapping_ids or [])})
    if not ids:
        return 0
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            cursor = connection.execute(
                f"""
                UPDATE pk_mapowanie_wizyt
                SET czy_aktywne = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE mapowanie_id IN ({_placeholders(ids)})
                  AND czy_aktywne = 1
                """,
                tuple(ids),
            )
            return int(cursor.rowcount or 0)


def replace_mapping(visit_type_id, target_klocek_id) -> int:
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            _validate_block(connection, target_klocek_id)
            selected_ids = _validate_visit_type_ids(connection, [visit_type_id])
            conflicts = _active_conflicts(
                connection,
                target_klocek_id,
                selected_ids,
            )
            if conflicts:
                connection.execute(
                    f"""
                    UPDATE pk_mapowanie_wizyt
                    SET czy_aktywne = 0,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE mapowanie_id IN ({
                        _placeholders([row["mapowanie_id"] for row in conflicts])
                    })
                    """,
                    tuple(row["mapowanie_id"] for row in conflicts),
                )
            existing = connection.execute(
                """
                SELECT mapowanie_id
                FROM pk_mapowanie_wizyt
                WHERE klocek_id = ?
                  AND rodzaj_wizyty_id = ?
                """,
                (int(target_klocek_id), int(selected_ids[0])),
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
                (int(target_klocek_id), int(selected_ids[0])),
            )
            return int(cursor.lastrowid)


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
    remove_mapping(mapowanie_id)


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
    "assign_visit_types",
    "delete_visit_mapping",
    "get_active_parameter_codes_for_block",
    "get_block_for_visit_parameter",
    "list_blocks_with_visit_types",
    "list_mapping_blocks",
    "list_mappings_for_block",
    "list_visit_mappings",
    "remove_mapping",
    "remove_mappings",
    "replace_mapping",
    "VisitTypeMappingConflict",
]
