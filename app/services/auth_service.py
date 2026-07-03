import base64
import hashlib
import hmac
import secrets
from contextlib import closing
from dataclasses import dataclass

from local_db import create_local_connection, initialize_local_db


PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 310_000
PASSWORD_SALT_BYTES = 16
MAX_FAILED_LOGINS = 5
MIN_PASSWORD_LENGTH = 8


class AuthenticationError(ValueError):
    pass


class AuthorizationError(PermissionError):
    pass


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: int
    login: str
    full_name: str
    must_change_password: bool
    roles: frozenset[str]

    @property
    def is_admin(self) -> bool:
        return "ADMIN" in self.roles


def hash_password(password: str) -> str:
    password = str(password or "")
    if not password:
        raise ValueError("Hasło nie może być puste")
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return "$".join(
        (
            PASSWORD_SCHEME,
            str(PASSWORD_ITERATIONS),
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(digest).decode("ascii"),
        )
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        scheme, iterations, salt_value, digest_value = encoded_hash.split(
            "$", 3
        )
        if scheme != PASSWORD_SCHEME:
            return False
        salt = base64.b64decode(salt_value, validate=True)
        expected = base64.b64decode(digest_value, validate=True)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            str(password or "").encode("utf-8"),
            salt,
            int(iterations),
        )
        return hmac.compare_digest(actual, expected)
    except (AttributeError, TypeError, ValueError):
        return False


def _roles_for_user(connection, user_id) -> frozenset[str]:
    rows = connection.execute(
        """
        SELECT r.code
        FROM pk_roles r
        JOIN pk_user_roles ur ON ur.role_id = r.role_id
        WHERE ur.user_id = ?
        ORDER BY r.code
        """,
        (user_id,),
    ).fetchall()
    return frozenset(str(row["code"]).upper() for row in rows)


def _authenticated_user(connection, row) -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=int(row["user_id"]),
        login=row["login"],
        full_name=row["full_name"],
        must_change_password=bool(row["must_change_password"]),
        roles=_roles_for_user(connection, row["user_id"]),
    )


def _login_error():
    return AuthenticationError(
        "Nieprawidłowy login lub hasło albo konto jest zablokowane"
    )


def login(login, password) -> AuthenticatedUser:
    normalized_login = str(login or "").strip()
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        row = connection.execute(
            """
            SELECT
                user_id,
                login,
                full_name,
                password_hash,
                must_change_password,
                is_active,
                failed_login_count,
                locked_at
            FROM pk_users
            WHERE login = ? COLLATE NOCASE
            """,
            (normalized_login,),
        ).fetchone()
        if row is None:
            raise _login_error()
        if not row["is_active"] or row["locked_at"]:
            raise _login_error()
        if not verify_password(password, row["password_hash"]):
            failed_count = int(row["failed_login_count"] or 0) + 1
            connection.execute(
                """
                UPDATE pk_users
                SET failed_login_count = ?,
                    locked_at = CASE
                        WHEN ? >= ? THEN CURRENT_TIMESTAMP
                        ELSE locked_at
                    END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (
                    failed_count,
                    failed_count,
                    MAX_FAILED_LOGINS,
                    row["user_id"],
                ),
            )
            connection.commit()
            raise _login_error()

        connection.execute(
            """
            UPDATE pk_users
            SET failed_login_count = 0,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (row["user_id"],),
        )
        connection.commit()
        return _authenticated_user(connection, row)


def _validate_new_password(new_password) -> str:
    password = str(new_password or "")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Nowe hasło musi mieć co najmniej {MIN_PASSWORD_LENGTH} znaków"
        )
    return password


def change_password(user_id, old_password, new_password) -> None:
    password = _validate_new_password(new_password)
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        row = connection.execute(
            """
            SELECT password_hash, is_active, locked_at
            FROM pk_users
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        if (
            row is None
            or not row["is_active"]
            or row["locked_at"]
            or not verify_password(old_password, row["password_hash"])
        ):
            raise AuthenticationError("Dotychczasowe hasło jest nieprawidłowe")
        if verify_password(password, row["password_hash"]):
            raise ValueError("Nowe hasło musi różnić się od dotychczasowego")
        with connection:
            connection.execute(
                """
                UPDATE pk_users
                SET password_hash = ?,
                    must_change_password = 0,
                    failed_login_count = 0,
                    locked_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (hash_password(password), user_id),
            )


def _require_admin(connection, admin_user_id):
    row = connection.execute(
        """
        SELECT 1
        FROM pk_users u
        JOIN pk_user_roles ur ON ur.user_id = u.user_id
        JOIN pk_roles r ON r.role_id = ur.role_id
        WHERE u.user_id = ?
          AND u.is_active = 1
          AND u.locked_at IS NULL
          AND r.code = 'ADMIN' COLLATE NOCASE
        """,
        (admin_user_id,),
    ).fetchone()
    if row is None:
        raise AuthorizationError("Operacja wymaga roli ADMIN")


def reset_password(admin_user_id, target_user_id, new_password) -> None:
    password = _validate_new_password(new_password)
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        with connection:
            _require_admin(connection, admin_user_id)
            cursor = connection.execute(
                """
                UPDATE pk_users
                SET password_hash = ?,
                    must_change_password = 1,
                    failed_login_count = 0,
                    locked_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (hash_password(password), target_user_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("Nie znaleziono użytkownika")


def _is_last_active_admin(connection, user_id) -> bool:
    target_is_admin = connection.execute(
        """
        SELECT 1
        FROM pk_user_roles ur
        JOIN pk_roles r ON r.role_id = ur.role_id
        WHERE ur.user_id = ?
          AND r.code = 'ADMIN' COLLATE NOCASE
        """,
        (user_id,),
    ).fetchone()
    if target_is_admin is None:
        return False
    row = connection.execute(
        """
        SELECT COUNT(DISTINCT u.user_id)
        FROM pk_users u
        JOIN pk_user_roles ur ON ur.user_id = u.user_id
        JOIN pk_roles r ON r.role_id = ur.role_id
        WHERE u.is_active = 1
          AND u.locked_at IS NULL
          AND r.code = 'ADMIN' COLLATE NOCASE
        """
    ).fetchone()
    return row[0] <= 1


def block_user(user_id) -> None:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        with connection:
            if _is_last_active_admin(connection, user_id):
                raise ValueError(
                    "Nie można zablokować ostatniego aktywnego administratora"
                )
            cursor = connection.execute(
                """
                UPDATE pk_users
                SET is_active = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (user_id,),
            )
            if cursor.rowcount == 0:
                raise ValueError("Nie znaleziono użytkownika")


def unblock_user(user_id) -> None:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        with connection:
            cursor = connection.execute(
                """
                UPDATE pk_users
                SET is_active = 1,
                    failed_login_count = 0,
                    locked_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (user_id,),
            )
            if cursor.rowcount == 0:
                raise ValueError("Nie znaleziono użytkownika")


def list_roles() -> list[dict]:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        rows = connection.execute(
            """
            SELECT role_id, code, name
            FROM pk_roles
            ORDER BY code
            """
        ).fetchall()
    return [dict(row) for row in rows]


def list_users(admin_user_id) -> list[dict]:
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        _require_admin(connection, admin_user_id)
        rows = connection.execute(
            """
            SELECT
                u.user_id,
                u.login,
                u.full_name,
                u.must_change_password,
                u.is_active,
                u.failed_login_count,
                u.locked_at,
                u.created_at,
                u.updated_at,
                COALESCE(GROUP_CONCAT(r.code, ', '), '') AS roles
            FROM pk_users u
            LEFT JOIN pk_user_roles ur ON ur.user_id = u.user_id
            LEFT JOIN pk_roles r ON r.role_id = ur.role_id
            GROUP BY u.user_id
            ORDER BY u.login COLLATE NOCASE
            """
        ).fetchall()
    return [dict(row) for row in rows]


def _normalized_role_codes(role_codes):
    codes = {
        str(code).strip().upper()
        for code in role_codes
        if code is not None and str(code).strip()
    }
    if not codes:
        raise ValueError("Użytkownik musi mieć co najmniej jedną rolę")
    return codes


def _replace_roles(connection, user_id, role_codes):
    codes = _normalized_role_codes(role_codes)
    placeholders = ", ".join("?" for _ in codes)
    rows = connection.execute(
        f"""
        SELECT role_id, code
        FROM pk_roles
        WHERE code IN ({placeholders})
        """,
        tuple(codes),
    ).fetchall()
    found_codes = {str(row["code"]).upper() for row in rows}
    if found_codes != codes:
        missing = ", ".join(sorted(codes - found_codes))
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
        [(user_id, row["role_id"]) for row in rows],
    )


def create_user(
    admin_user_id,
    login,
    full_name,
    password,
    role_codes,
) -> int:
    normalized_login = str(login or "").strip()
    normalized_name = str(full_name or "").strip()
    if not normalized_login:
        raise ValueError("Login jest wymagany")
    if not normalized_name:
        raise ValueError("Imię i nazwisko jest wymagane")
    password = _validate_new_password(password)
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        with connection:
            _require_admin(connection, admin_user_id)
            cursor = connection.execute(
                """
                INSERT INTO pk_users(
                    login,
                    full_name,
                    password_hash,
                    must_change_password
                )
                VALUES (?, ?, ?, 1)
                """,
                (
                    normalized_login,
                    normalized_name,
                    hash_password(password),
                ),
            )
            user_id = int(cursor.lastrowid)
            _replace_roles(connection, user_id, role_codes)
    return user_id


def set_user_roles(admin_user_id, user_id, role_codes) -> None:
    codes = _normalized_role_codes(role_codes)
    initialize_local_db()
    with closing(create_local_connection()) as connection:
        with connection:
            _require_admin(connection, admin_user_id)
            exists = connection.execute(
                "SELECT 1 FROM pk_users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if exists is None:
                raise ValueError("Nie znaleziono użytkownika")
            if "ADMIN" not in codes and _is_last_active_admin(
                connection, user_id
            ):
                raise ValueError(
                    "Nie można odebrać roli ostatniemu administratorowi"
                )
            _replace_roles(connection, user_id, codes)
