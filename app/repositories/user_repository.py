from contextlib import closing

from app.repositories.db_connection import (
    create_connection,
    initialize_database,
)


USER_COLUMNS = """
    user_id,
    login,
    full_name,
    password_hash,
    must_change_password,
    is_active,
    failed_login_count,
    locked_at,
    created_at,
    updated_at
"""


def get_user(user_id):
    initialize_database()
    with closing(create_connection()) as connection:
        row = connection.execute(
            f"""
            SELECT {USER_COLUMNS}
            FROM pk_users
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def get_user_by_login(login):
    initialize_database()
    with closing(create_connection()) as connection:
        row = connection.execute(
            f"""
            SELECT {USER_COLUMNS}
            FROM pk_users
            WHERE login = ? COLLATE NOCASE
            """,
            (str(login or "").strip(),),
        ).fetchone()
    return dict(row) if row is not None else None


def list_users() -> list[dict]:
    initialize_database()
    with closing(create_connection()) as connection:
        rows = connection.execute(
            f"""
            SELECT {USER_COLUMNS}
            FROM pk_users
            ORDER BY login COLLATE NOCASE
            """
        ).fetchall()
    return [dict(row) for row in rows]


def create_user_record(
    login,
    full_name,
    password_hash,
    must_change_password=1,
) -> int:
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO pk_users(
                    login,
                    full_name,
                    password_hash,
                    must_change_password
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    str(login).strip(),
                    str(full_name).strip(),
                    password_hash,
                    1 if must_change_password else 0,
                ),
            )
            return int(cursor.lastrowid)


def set_user_active(user_id, is_active) -> None:
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            cursor = connection.execute(
                """
                UPDATE pk_users
                SET is_active = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (1 if is_active else 0, user_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("Nie znaleziono użytkownika")

