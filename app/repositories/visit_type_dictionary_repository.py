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


def _normalize_code(value):
    return _required_text(value, "parametr_kod").upper()


def _bool01(value, default=1):
    if value is None:
        return int(default)
    if isinstance(value, bool):
        return 1 if value else 0
    text = str(value).strip().upper()
    if text in {"1", "T", "TAK", "Y", "YES", "TRUE", "A"}:
        return 1
    if text in {"0", "N", "NIE", "NO", "FALSE", "F"}:
        return 0
    return int(default)


def _record_value(record, *names, default=None):
    for name in names:
        if isinstance(record, dict) and name in record:
            return record[name]
        if hasattr(record, name):
            return getattr(record, name)
    return default


def _fetch_one_by_code(connection, code):
    return connection.execute(
        """
        SELECT
            rodzaj_wizyty_id,
            parametr_kod,
            parametr_nazwa,
            czy_aktualny_eskulap,
            czy_aktywny_kompas
        FROM pk_rodzaje_wizyt_eskulap
        WHERE UPPER(parametr_kod) = ?
        """,
        (code,),
    ).fetchone()


def list_visit_types(active_only=False) -> list[dict]:
    initialize_database()
    where_clause = (
        "WHERE r.czy_aktualny_eskulap = 1 AND r.czy_aktywny_kompas = 1"
        if active_only
        else ""
    )
    with closing(create_connection()) as connection:
        rows = connection.execute(
            f"""
            SELECT
                r.rodzaj_wizyty_id,
                r.parametr_kod,
                r.parametr_nazwa,
                r.czy_aktualny_eskulap,
                r.czy_aktywny_kompas,
                r.first_seen_at,
                r.last_seen_at,
                r.synchronized_at,
                r.created_at,
                r.updated_at,
                m.mapowanie_id,
                m.klocek_id,
                m.czy_aktywne AS czy_mapowanie_aktywne,
                k.kod AS klocek_kod,
                k.nazwa AS klocek_nazwa,
                k.kolor AS klocek_kolor,
                k.kolor_tekstu AS klocek_kolor_tekstu,
                typ.kod AS typ_kod,
                typ.nazwa AS typ_nazwa
            FROM pk_rodzaje_wizyt_eskulap r
            LEFT JOIN pk_mapowanie_wizyt m
                ON m.rodzaj_wizyty_id = r.rodzaj_wizyty_id
               AND m.czy_aktywne = 1
            LEFT JOIN pk_klocki k
                ON k.klocek_id = m.klocek_id
            LEFT JOIN pk_typy_elementow typ
                ON typ.typ_id = k.typ_elementu_id
            {where_clause}
            ORDER BY r.parametr_nazwa, r.parametr_kod
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_by_code(code):
    normalized = _normalize_code(code)
    initialize_database()
    with closing(create_connection()) as connection:
        row = _fetch_one_by_code(connection, normalized)
    return dict(row) if row is not None else None


def upsert_from_eskulap(records, connection=None) -> dict:
    own_connection = connection is None
    connection = connection or create_connection()
    stats = {
        "added": 0,
        "updated": 0,
        "unchanged": 0,
        "seen_codes": set(),
    }
    try:
        context = connection if own_connection else _null_context(connection)
        with context:
            for record in records:
                code = _normalize_code(
                    _record_value(record, "code", "parametr_kod")
                )
                name = _required_text(
                    _record_value(record, "name", "parametr_nazwa"),
                    "parametr_nazwa",
                )
                is_current = _bool01(
                    _record_value(
                        record,
                        "is_active",
                        "czy_aktualne",
                        "parametr_czy_aktualne",
                    ),
                    default=1,
                )
                stats["seen_codes"].add(code)
                existing = _fetch_one_by_code(connection, code)
                if existing is None:
                    connection.execute(
                        """
                        INSERT INTO pk_rodzaje_wizyt_eskulap(
                            parametr_kod,
                            parametr_nazwa,
                            czy_aktualny_eskulap,
                            czy_aktywny_kompas,
                            first_seen_at,
                            last_seen_at,
                            synchronized_at
                        )
                        VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP,
                                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """,
                        (code, name, is_current),
                    )
                    stats["added"] += 1
                    continue

                changed = (
                    str(existing["parametr_nazwa"] or "") != name
                    or int(existing["czy_aktualny_eskulap"]) != is_current
                )
                connection.execute(
                    """
                    UPDATE pk_rodzaje_wizyt_eskulap
                    SET parametr_nazwa = ?,
                        czy_aktualny_eskulap = ?,
                        last_seen_at = CURRENT_TIMESTAMP,
                        synchronized_at = CURRENT_TIMESTAMP,
                        updated_at = CASE
                            WHEN parametr_nazwa <> ?
                              OR czy_aktualny_eskulap <> ?
                            THEN CURRENT_TIMESTAMP
                            ELSE updated_at
                        END
                    WHERE rodzaj_wizyty_id = ?
                    """,
                    (
                        name,
                        is_current,
                        name,
                        is_current,
                        existing["rodzaj_wizyty_id"],
                    ),
                )
                stats["updated" if changed else "unchanged"] += 1
    finally:
        if own_connection:
            connection.close()
    return stats


def deactivate_missing(codes_seen, connection=None) -> int:
    codes = {
        str(code or "").strip().upper()
        for code in (codes_seen or [])
        if str(code or "").strip()
    }
    own_connection = connection is None
    connection = connection or create_connection()
    try:
        context = connection if own_connection else _null_context(connection)
        with context:
            if codes:
                placeholders = ",".join("?" for _ in codes)
                cursor = connection.execute(
                    f"""
                    UPDATE pk_rodzaje_wizyt_eskulap
                    SET czy_aktualny_eskulap = 0,
                        synchronized_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE UPPER(parametr_kod) NOT IN ({placeholders})
                      AND czy_aktualny_eskulap = 1
                    """,
                    tuple(sorted(codes)),
                )
            else:
                cursor = connection.execute(
                    """
                    UPDATE pk_rodzaje_wizyt_eskulap
                    SET czy_aktualny_eskulap = 0,
                        synchronized_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE czy_aktualny_eskulap = 1
                    """
                )
    finally:
        if own_connection:
            connection.close()
    return int(cursor.rowcount or 0)


def get_visit_type_names(codes) -> dict[str, str]:
    normalized = sorted(
        {
            str(code or "").strip().upper()
            for code in (codes or [])
            if str(code or "").strip()
        }
    )
    if not normalized:
        return {}
    initialize_database()
    placeholders = ",".join("?" for _ in normalized)
    with closing(create_connection()) as connection:
        rows = connection.execute(
            f"""
            SELECT parametr_kod, parametr_nazwa
            FROM pk_rodzaje_wizyt_eskulap
            WHERE UPPER(parametr_kod) IN ({placeholders})
            """,
            tuple(normalized),
        ).fetchall()
    return {
        str(row["parametr_kod"]).strip().upper(): str(row["parametr_nazwa"])
        for row in rows
    }


def get_sync_summary() -> dict:
    initialize_database()
    with closing(create_connection()) as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN czy_aktualny_eskulap = 1 THEN 1 ELSE 0 END)
                    AS current_count,
                SUM(CASE WHEN czy_aktywny_kompas = 1 THEN 1 ELSE 0 END)
                    AS kompas_active_count,
                MAX(synchronized_at) AS last_synchronized_at
            FROM pk_rodzaje_wizyt_eskulap
            """
        ).fetchone()
    return dict(row or {})


def set_kompas_active(rodzaj_wizyty_id, active) -> None:
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            cursor = connection.execute(
                """
                UPDATE pk_rodzaje_wizyt_eskulap
                SET czy_aktywny_kompas = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE rodzaj_wizyty_id = ?
                """,
                (1 if active else 0, int(rodzaj_wizyty_id)),
            )
            if cursor.rowcount == 0:
                raise ValueError("Nie znaleziono rodzaju wizyty")


class _null_context:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self.value

    def __exit__(self, exc_type, exc, tb):
        return False


__all__ = [
    "deactivate_missing",
    "get_by_code",
    "get_sync_summary",
    "get_visit_type_names",
    "list_visit_types",
    "set_kompas_active",
    "upsert_from_eskulap",
]
