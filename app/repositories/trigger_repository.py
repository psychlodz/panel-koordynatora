from contextlib import closing

from app.repositories.db_connection import (
    create_connection,
    initialize_database,
)


TRIGGER_TYPES = {
    "START_EPIZODU",
    "PO_ZAKONCZENIU",
    "PO_ZLECENIU",
    "PO_WYNIKU",
    "RECZNIE",
}


def _trigger_type(value) -> str:
    trigger_type = str(value or "").strip().upper()
    if trigger_type not in TRIGGER_TYPES:
        raise ValueError("Nieprawidłowy typ wyzwalacza")
    return trigger_type


def _optional_text(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _element_pathway_id(connection, element_id) -> int:
    row = connection.execute(
        """
        SELECT sciezka_id
        FROM pk_sciezka_elementy
        WHERE element_id = ?
        """,
        (element_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Nie znaleziono elementu o ID {element_id}")
    return int(row["sciezka_id"])


def _validate_source(connection, element_id, trigger_element_id):
    if trigger_element_id is None:
        return
    target_pathway = _element_pathway_id(connection, element_id)
    source_pathway = _element_pathway_id(connection, trigger_element_id)
    if target_pathway != source_pathway:
        raise ValueError(
            "Element źródłowy musi należeć do tej samej ścieżki"
        )


def _ensure_unique_episode_start(
    connection,
    element_id,
    trigger_type,
    exclude_trigger_id=None,
):
    if trigger_type != "START_EPIZODU":
        return
    row = connection.execute(
        """
        SELECT trigger_id
        FROM pk_wyzwalacze
        WHERE element_id = ?
          AND trigger_type = 'START_EPIZODU'
          AND (? IS NULL OR trigger_id <> ?)
        LIMIT 1
        """,
        (element_id, exclude_trigger_id, exclude_trigger_id),
    ).fetchone()
    if row is not None:
        raise ValueError(
            "Wyzwalacz START_EPIZODU może istnieć tylko raz dla elementu"
        )


def list_triggers(element_id) -> list[dict]:
    initialize_database()
    with closing(create_connection()) as connection:
        rows = connection.execute(
            """
            SELECT
                w.trigger_id,
                w.element_id,
                w.trigger_type,
                w.trigger_element_id,
                w.opis,
                w.created_at,
                w.updated_at,
                e.lp AS trigger_element_lp,
                e.nazwa_w_sciezce AS trigger_element_nazwa,
                k.kod AS trigger_element_klocek
            FROM pk_wyzwalacze w
            LEFT JOIN pk_sciezka_elementy e
                ON e.element_id = w.trigger_element_id
            LEFT JOIN pk_klocki k
                ON k.klocek_id = e.klocek_id
            WHERE w.element_id = ?
            ORDER BY w.trigger_type, w.trigger_id
            """,
            (element_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def create_trigger(
    element_id,
    trigger_type,
    trigger_element_id=None,
    opis=None,
) -> int:
    normalized_type = _trigger_type(trigger_type)
    if normalized_type == "START_EPIZODU":
        trigger_element_id = None
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            _element_pathway_id(connection, element_id)
            _validate_source(connection, element_id, trigger_element_id)
            _ensure_unique_episode_start(
                connection, element_id, normalized_type
            )
            cursor = connection.execute(
                """
                INSERT INTO pk_wyzwalacze(
                    element_id,
                    trigger_type,
                    trigger_element_id,
                    opis
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    element_id,
                    normalized_type,
                    trigger_element_id,
                    _optional_text(opis),
                ),
            )
            trigger_id = cursor.lastrowid
    return int(trigger_id)


def update_trigger(
    trigger_id,
    trigger_type,
    trigger_element_id=None,
    opis=None,
) -> int:
    normalized_type = _trigger_type(trigger_type)
    if normalized_type == "START_EPIZODU":
        trigger_element_id = None
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            trigger = connection.execute(
                """
                SELECT element_id
                FROM pk_wyzwalacze
                WHERE trigger_id = ?
                """,
                (trigger_id,),
            ).fetchone()
            if trigger is None:
                raise ValueError(f"Nie znaleziono wyzwalacza o ID {trigger_id}")
            element_id = trigger["element_id"]
            _validate_source(connection, element_id, trigger_element_id)
            _ensure_unique_episode_start(
                connection,
                element_id,
                normalized_type,
                exclude_trigger_id=trigger_id,
            )
            connection.execute(
                """
                UPDATE pk_wyzwalacze
                SET trigger_type = ?,
                    trigger_element_id = ?,
                    opis = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE trigger_id = ?
                """,
                (
                    normalized_type,
                    trigger_element_id,
                    _optional_text(opis),
                    trigger_id,
                ),
            )
    return int(trigger_id)


def delete_trigger(trigger_id) -> None:
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            cursor = connection.execute(
                """
                DELETE FROM pk_wyzwalacze
                WHERE trigger_id = ?
                """,
                (trigger_id,),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Nie znaleziono wyzwalacza o ID {trigger_id}")
