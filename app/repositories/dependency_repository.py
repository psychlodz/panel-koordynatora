from contextlib import closing

from local_db import create_local_connection, initialize_local_db


DEPENDENCY_TYPES = {"KOLEJNOSC", "WARUNEK"}


def _dependency_type(value) -> str:
    dependency_type = str(value or "").strip().upper()
    if dependency_type not in DEPENDENCY_TYPES:
        raise ValueError("Typ zależności musi być KOLEJNOSC albo WARUNEK")
    return dependency_type


def _optional_text(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _ensure_elements_in_pathway(
    connection,
    sciezka_id,
    element_od_id,
    element_do_id,
):
    row = connection.execute(
        """
        SELECT COUNT(DISTINCT element_id) AS element_count
        FROM pk_sciezka_elementy
        WHERE sciezka_id = ?
          AND element_id IN (?, ?)
        """,
        (sciezka_id, element_od_id, element_do_id),
    ).fetchone()
    if row["element_count"] != 2:
        raise ValueError("Oba elementy muszą należeć do wybranej ścieżki")


def _validate_cycle(
    connection,
    sciezka_id,
    element_od_id,
    element_do_id,
    exclude_dependency_id=None,
) -> bool:
    if int(element_od_id) == int(element_do_id):
        return False

    _ensure_elements_in_pathway(
        connection, sciezka_id, element_od_id, element_do_id
    )
    rows = connection.execute(
        """
        SELECT zaleznosc_id, element_od_id, element_do_id
        FROM pk_sciezka_zaleznosci
        WHERE sciezka_id = ?
        """,
        (sciezka_id,),
    ).fetchall()

    graph = {}
    for row in rows:
        if (
            exclude_dependency_id is not None
            and row["zaleznosc_id"] == exclude_dependency_id
        ):
            continue
        graph.setdefault(row["element_od_id"], set()).add(
            row["element_do_id"]
        )

    target = int(element_od_id)
    stack = [int(element_do_id)]
    visited = set()
    while stack:
        current = stack.pop()
        if current == target:
            return False
        if current in visited:
            continue
        visited.add(current)
        stack.extend(graph.get(current, ()))
    return True


def list_dependencies(sciezka_id) -> list[dict]:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        rows = connection.execute(
            """
            SELECT
                z.zaleznosc_id,
                z.sciezka_id,
                z.element_od_id,
                z.element_do_id,
                z.typ,
                z.opis,
                z.created_at,
                z.updated_at,
                e_od.lp AS element_od_lp,
                e_od.nazwa_w_sciezce AS element_od_nazwa,
                k_od.kod AS element_od_klocek,
                e_do.lp AS element_do_lp,
                e_do.nazwa_w_sciezce AS element_do_nazwa,
                k_do.kod AS element_do_klocek
            FROM pk_sciezka_zaleznosci z
            JOIN pk_sciezka_elementy e_od
                ON e_od.element_id = z.element_od_id
            JOIN pk_klocki k_od
                ON k_od.klocek_id = e_od.klocek_id
            JOIN pk_sciezka_elementy e_do
                ON e_do.element_id = z.element_do_id
            JOIN pk_klocki k_do
                ON k_do.klocek_id = e_do.klocek_id
            WHERE z.sciezka_id = ?
            ORDER BY e_od.lp, e_do.lp, z.zaleznosc_id
            """,
            (sciezka_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def validate_cycle(
    sciezka_id,
    element_od_id,
    element_do_id,
    exclude_dependency_id=None,
) -> bool:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        return _validate_cycle(
            connection,
            sciezka_id,
            element_od_id,
            element_do_id,
            exclude_dependency_id,
        )


def create_dependency(
    sciezka_id,
    element_od_id,
    element_do_id,
    typ,
    opis=None,
) -> int:
    dependency_type = _dependency_type(typ)
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        with connection:
            if not _validate_cycle(
                connection,
                sciezka_id,
                element_od_id,
                element_do_id,
            ):
                raise ValueError(
                    "Zależność do samego elementu lub tworząca cykl jest niedozwolona"
                )
            cursor = connection.execute(
                """
                INSERT INTO pk_sciezka_zaleznosci(
                    sciezka_id,
                    element_od_id,
                    element_do_id,
                    typ,
                    opis
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    sciezka_id,
                    element_od_id,
                    element_do_id,
                    dependency_type,
                    _optional_text(opis),
                ),
            )
            dependency_id = cursor.lastrowid
    return int(dependency_id)


def update_dependency(
    zaleznosc_id,
    element_od_id,
    element_do_id,
    typ,
    opis=None,
) -> int:
    dependency_type = _dependency_type(typ)
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        with connection:
            dependency = connection.execute(
                """
                SELECT sciezka_id
                FROM pk_sciezka_zaleznosci
                WHERE zaleznosc_id = ?
                """,
                (zaleznosc_id,),
            ).fetchone()
            if dependency is None:
                raise ValueError(
                    f"Nie znaleziono zależności o ID {zaleznosc_id}"
                )
            sciezka_id = dependency["sciezka_id"]
            if not _validate_cycle(
                connection,
                sciezka_id,
                element_od_id,
                element_do_id,
                exclude_dependency_id=zaleznosc_id,
            ):
                raise ValueError(
                    "Zależność do samego elementu lub tworząca cykl jest niedozwolona"
                )
            connection.execute(
                """
                UPDATE pk_sciezka_zaleznosci
                SET element_od_id = ?,
                    element_do_id = ?,
                    typ = ?,
                    opis = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE zaleznosc_id = ?
                """,
                (
                    element_od_id,
                    element_do_id,
                    dependency_type,
                    _optional_text(opis),
                    zaleznosc_id,
                ),
            )
    return int(zaleznosc_id)


def delete_dependency(zaleznosc_id) -> None:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        with connection:
            cursor = connection.execute(
                """
                DELETE FROM pk_sciezka_zaleznosci
                WHERE zaleznosc_id = ?
                """,
                (zaleznosc_id,),
            )
            if cursor.rowcount == 0:
                raise ValueError(
                    f"Nie znaleziono zależności o ID {zaleznosc_id}"
                )
