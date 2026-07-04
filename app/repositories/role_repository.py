from contextlib import closing

from app.repositories.db_connection import (
    create_connection,
    initialize_database,
)


def list_roles() -> list[dict]:
    initialize_database()
    with closing(create_connection()) as connection:
        rows = connection.execute(
            """
            SELECT role_id, code, name
            FROM pk_roles
            ORDER BY code
            """
        ).fetchall()
    return [dict(row) for row in rows]


def list_user_roles(user_id) -> list[dict]:
    initialize_database()
    with closing(create_connection()) as connection:
        rows = connection.execute(
            """
            SELECT r.role_id, r.code, r.name
            FROM pk_roles r
            JOIN pk_user_roles ur ON ur.role_id = r.role_id
            WHERE ur.user_id = ?
            ORDER BY r.code
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def replace_user_roles(user_id, role_codes) -> None:
    codes = {
        str(code).strip().upper()
        for code in role_codes
        if code is not None and str(code).strip()
    }
    if not codes:
        raise ValueError("Użytkownik musi mieć co najmniej jedną rolę")

    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            placeholders = ", ".join("?" for _ in codes)
            roles = connection.execute(
                f"""
                SELECT role_id, code
                FROM pk_roles
                WHERE code IN ({placeholders})
                """,
                tuple(codes),
            ).fetchall()
            found = {str(role["code"]).upper() for role in roles}
            if found != codes:
                missing = ", ".join(sorted(codes - found))
                raise ValueError(f"Nieznane role: {missing}")
            connection.execute(
                "DELETE FROM pk_user_roles WHERE user_id = ?",
                (user_id,),
            )
            connection.executemany(
                """
                INSERT INTO pk_user_roles(user_id, role_id)
                VALUES (?, ?)
                """,
                [(user_id, role["role_id"]) for role in roles],
            )

