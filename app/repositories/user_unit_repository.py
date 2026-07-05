from contextlib import closing

from app.repositories.db_connection import (
    create_connection,
    initialize_database,
)


def _unit_id(jo_id):
    value = "" if jo_id is None else str(jo_id).strip()
    if not value:
        raise ValueError("Identyfikator jednostki jest wymagany")
    return value


def _optional_text(value):
    text = str(value or "").strip()
    return text or None


def _ensure_default(connection, user_id):
    default = connection.execute(
        """
        SELECT jo_id
        FROM pk_user_units
        WHERE user_id = ?
          AND is_default = 1
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    if default is not None:
        return
    first = connection.execute(
        """
        SELECT jo_id
        FROM pk_user_units
        WHERE user_id = ?
        ORDER BY created_at, jo_id
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    if first is not None:
        connection.execute(
            """
            UPDATE pk_user_units
            SET is_default = 1
            WHERE user_id = ?
              AND jo_id = ?
            """,
            (user_id, first["jo_id"]),
        )


def list_user_units(user_id) -> list[dict]:
    initialize_database()
    with closing(create_connection()) as connection:
        rows = connection.execute(
            """
            SELECT
                user_id,
                jo_id,
                jo_symbol,
                jo_nazwa,
                is_default,
                created_at
            FROM pk_user_units
            WHERE user_id = ?
            ORDER BY is_default DESC,
                     jo_symbol COLLATE NOCASE,
                     jo_nazwa COLLATE NOCASE,
                     jo_id
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def assign_unit_to_user(
    user_id,
    jo_id,
    jo_symbol,
    jo_nazwa,
) -> None:
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO pk_user_units(
                    user_id,
                    jo_id,
                    jo_symbol,
                    jo_nazwa
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, jo_id) DO UPDATE SET
                    jo_symbol = excluded.jo_symbol,
                    jo_nazwa = excluded.jo_nazwa
                """,
                (
                    user_id,
                    _unit_id(jo_id),
                    _optional_text(jo_symbol),
                    _optional_text(jo_nazwa),
                ),
            )
            _ensure_default(connection, user_id)


def remove_unit_from_user(user_id, jo_id) -> None:
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """
                DELETE FROM pk_user_units
                WHERE user_id = ?
                  AND jo_id = ?
                """,
                (user_id, _unit_id(jo_id)),
            )
            if cursor.rowcount == 0:
                raise ValueError("Jednostka nie była przypisana użytkownikowi")
            _ensure_default(connection, user_id)


def set_default_unit(user_id, jo_id) -> None:
    jo_id = _unit_id(jo_id)
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            exists = connection.execute(
                """
                SELECT 1
                FROM pk_user_units
                WHERE user_id = ?
                  AND jo_id = ?
                """,
                (user_id, jo_id),
            ).fetchone()
            if exists is None:
                raise ValueError("Jednostka nie jest przypisana użytkownikowi")
            connection.execute(
                """
                UPDATE pk_user_units
                SET is_default = CASE WHEN jo_id = ? THEN 1 ELSE 0 END
                WHERE user_id = ?
                """,
                (jo_id, user_id),
            )


def get_default_unit(user_id):
    initialize_database()
    with closing(create_connection()) as connection:
        row = connection.execute(
            """
            SELECT
                user_id,
                jo_id,
                jo_symbol,
                jo_nazwa,
                is_default,
                created_at
            FROM pk_user_units
            WHERE user_id = ?
            ORDER BY is_default DESC,
                     created_at,
                     jo_id
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    return dict(row) if row is not None else None
