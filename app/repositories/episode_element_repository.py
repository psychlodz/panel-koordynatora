import json
from contextlib import closing

from app.repositories.db_connection import (
    create_connection,
    initialize_database,
)


COMPLETED_STATUSES = {
    "ZAKONCZONE",
    "ZAKOŃCZONE",
    "ZREALIZOWANO",
    "ZREALIZOWANE",
}
ACTIVE_TASK_STATUSES = {
    "DO_ZAPLANOWANIA",
    "OCZEKUJE_NA_ESKULAP",
    "OCZEKUJE NA ESKULAP",
    "ZAPLANOWANE",
    "ZAPLANOWANO",
    "W_REALIZACJI",
    "W REALIZACJI",
}
SOURCE_CONSULTATION = "ESKULAP_KONSULTACJE"
SOURCE_IMAGING = "ESKULAP_BADANIA_OBRAZOWE"
SPECIALIST_CONSULTATION_BLOCK_CODES = {"KONSULTACJA_SPECJALISTYCZNA"}
IMAGING_BLOCK_CODES = {"BADANIE_OBRAZOWE"}
TERMINAL_TASK_STATUSES = COMPLETED_STATUSES | {"ANULOWANE", "POMINIETE", "POMINIĘTE"}


def _status(value):
    return str(value or "").strip().upper()


def _json(data):
    if data is None:
        return None
    return json.dumps(data, ensure_ascii=False, default=str, sort_keys=True)


def _user_id(user_id):
    return str(user_id) if user_id is not None else None


def _row_dict(row):
    return dict(row) if row is not None else None


def _is_plannable_episode_element(row):
    block_code = str(row.get("klocek_kod") or "").strip().upper()
    source = str(row.get("eskulap_system") or "").strip().upper()
    return (
        block_code in SPECIALIST_CONSULTATION_BLOCK_CODES
        or block_code in IMAGING_BLOCK_CODES
        or source in {SOURCE_CONSULTATION, SOURCE_IMAGING}
    )


def _combined_plan_datetime(plan_date, time_from):
    if not plan_date or not time_from:
        return None
    return f"{str(plan_date)[:10]} {str(time_from)[:5]}:00"


def _is_invalid_specialist_consultation_assignment(row):
    block_code = str(row["klocek_kod"] or "").strip().upper()
    source = str(row["eskulap_system"] or "").strip().upper()
    return (
        block_code in SPECIALIST_CONSULTATION_BLOCK_CODES
        and source
        and source != SOURCE_CONSULTATION
    )


def _element_snapshot(connection, epizod_element_id):
    return _row_dict(
        connection.execute(
            """
            SELECT *
            FROM pk_epizod_elementy
            WHERE epizod_element_id = ?
            """,
            (epizod_element_id,),
        ).fetchone()
    )


def record_history(
    connection,
    epizod_element_id,
    operation,
    before=None,
    after=None,
    reason=None,
    user_id=None,
):
    element = after or before or _element_snapshot(connection, epizod_element_id)
    if element is not None and "epizod_id" not in element:
        element = _element_snapshot(connection, epizod_element_id)
    if element is None:
        raise ValueError(
            f"Nie znaleziono elementu epizodu o ID {epizod_element_id}"
        )
    connection.execute(
        """
        INSERT INTO pk_epizod_elementy_historia(
            epizod_element_id,
            epizod_id,
            operacja,
            dane_przed,
            dane_po,
            powod,
            changed_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            epizod_element_id,
            element["epizod_id"],
            operation,
            _json(before),
            _json(after),
            reason,
            _user_id(user_id),
        ),
    )


def copy_pathway_elements_for_episode(
    connection,
    epizod_id,
    sciezka_id,
    user_id=None,
) -> list[int]:
    existing = connection.execute(
        """
        SELECT epizod_element_id
        FROM pk_epizod_elementy
        WHERE epizod_id = ?
        LIMIT 1
        """,
        (epizod_id,),
    ).fetchone()
    if existing is not None:
        return [
            int(row["epizod_element_id"])
            for row in connection.execute(
                """
                SELECT epizod_element_id
                FROM pk_epizod_elementy
                WHERE epizod_id = ?
                ORDER BY lp, epizod_element_id
                """,
                (epizod_id,),
            ).fetchall()
        ]

    rows = connection.execute(
        """
        SELECT
            e.element_id,
            e.klocek_id,
            e.lp,
            e.nazwa_w_sciezce,
            e.min_liczba,
            e.max_liczba,
            e.termin_liczba,
            jc.jednostka_czasu_id,
            e.czy_obowiazkowy,
            e.czy_wymaga_zlecenia,
            e.czy_aktywny
        FROM pk_sciezka_elementy e
        LEFT JOIN pk_jednostki_czasu jc
            ON jc.kod = e.termin_jednostka
        WHERE e.sciezka_id = ?
        ORDER BY e.lp, e.element_id
        """,
        (sciezka_id,),
    ).fetchall()

    ids = []
    for row in rows:
        cursor = connection.execute(
            """
            INSERT INTO pk_epizod_elementy(
                epizod_id,
                sciezka_element_id,
                klocek_id,
                nazwa,
                lp,
                min_liczba,
                max_liczba,
                termin_liczba,
                jednostka_czasu_id,
                czy_wymagany,
                czy_wymaga_zlecenia,
                czy_aktywny,
                typ_pochodzenia,
                created_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'SCIEZKA', ?)
            """,
            (
                epizod_id,
                row["element_id"],
                row["klocek_id"],
                row["nazwa_w_sciezce"],
                row["lp"],
                row["min_liczba"],
                row["max_liczba"],
                row["termin_liczba"],
                row["jednostka_czasu_id"],
                row["czy_obowiazkowy"],
                row["czy_wymaga_zlecenia"],
                row["czy_aktywny"],
                _user_id(user_id),
            ),
        )
        epizod_element_id = int(cursor.lastrowid)
        ids.append(epizod_element_id)
        record_history(
            connection,
            epizod_element_id,
            "UTWORZENIE",
            after=_element_snapshot(connection, epizod_element_id),
            reason="Utworzenie epizodu z wzorcowej ścieżki",
            user_id=user_id,
        )
    return ids


def list_episode_elements(epizod_id, include_inactive=True) -> list[dict]:
    initialize_database()
    with closing(create_connection()) as connection:
        condition = "" if include_inactive else "AND ee.czy_aktywny = 1"
        rows = connection.execute(
            f"""
            SELECT
                ee.epizod_element_id,
                ee.epizod_id,
                ee.sciezka_element_id,
                ee.klocek_id,
                ee.element_zrodlowy_id,
                ee.nazwa,
                ee.lp,
                ee.min_liczba,
                ee.max_liczba,
                ee.termin_liczba,
                ee.jednostka_czasu_id,
                jc.kod AS jednostka_czasu_kod,
                jc.nazwa AS jednostka_czasu_nazwa,
                ee.termin_od_epizod_element_id,
                ee.czy_wymagany,
                ee.czy_wymaga_zlecenia,
                ee.czy_aktywny,
                ee.typ_pochodzenia,
                ee.powod_modyfikacji,
                k.kod AS klocek_kod,
                k.nazwa AS klocek_nazwa,
                k.kolor AS klocek_kolor,
                k.kolor_tekstu AS klocek_kolor_tekstu,
                z.zadanie_id,
                z.status,
                z.data_wymagana_do,
                z.data_zaplanowana,
                z.data_realizacji,
                z.kompas_plan_data,
                z.kompas_plan_godz_od,
                z.kompas_plan_godz_do,
                z.kompas_plan_uwagi,
                z.kompas_plan_user_id,
                z.kompas_plan_created_at,
                z.kompas_plan_updated_at,
                z.zrodlo,
                z.eskulap_system,
                z.eskulap_id,
                z.eskulap_pracownik,
                z.eskulap_data_wizyty,
                z.eskulap_plan_data,
                z.eskulap_plan_godz_od,
                z.eskulap_plan_godz_do,
                z.eskulap_rodzaj_wizyty,
                z.eskulap_decyzja,
                z.uwagi
            FROM pk_epizod_elementy ee
            JOIN pk_klocki k ON k.klocek_id = ee.klocek_id
            LEFT JOIN pk_jednostki_czasu jc
                ON jc.jednostka_czasu_id = ee.jednostka_czasu_id
            LEFT JOIN pk_zadania z
                ON z.epizod_element_id = ee.epizod_element_id
            WHERE ee.epizod_id = ?
              {condition}
            ORDER BY ee.lp, ee.epizod_element_id, z.zadanie_id
            """,
            (epizod_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_episode_element(epizod_element_id):
    initialize_database()
    with closing(create_connection()) as connection:
        return _element_snapshot(connection, epizod_element_id)


def _task_snapshot(connection, epizod_element_id):
    row = connection.execute(
        """
        SELECT
            z.*,
            k.kod AS klocek_kod,
            k.nazwa AS klocek_nazwa,
            ee.nazwa AS nazwa_elementu
        FROM pk_zadania z
        JOIN pk_epizod_elementy ee
            ON ee.epizod_element_id = z.epizod_element_id
        JOIN pk_klocki k
            ON k.klocek_id = ee.klocek_id
        WHERE z.epizod_element_id = ?
        ORDER BY z.zadanie_id
        LIMIT 1
        """,
        (epizod_element_id,),
    ).fetchone()
    return _row_dict(row)


def can_plan_element(epizod_element_id) -> dict:
    initialize_database()
    with closing(create_connection()) as connection:
        task = _task_snapshot(connection, epizod_element_id)
        if task is None:
            return {"allowed": False, "reason": "Nie znaleziono zadania elementu."}
        if not _is_plannable_episode_element(task):
            return {
                "allowed": False,
                "reason": "Ręczne planowanie dotyczy konsultacji i badań obrazowych.",
            }
        if _status(task.get("status")) in {
            "ZREALIZOWANA",
            "ZREALIZOWANO",
            "ZREALIZOWANE",
            "ANULOWANA",
            "ANULOWANE",
        }:
            return {
                "allowed": False,
                "reason": "Nie można planować elementu zrealizowanego albo anulowanego.",
            }
        return {"allowed": True, "reason": ""}


def plan_episode_element(
    epizod_element_id,
    plan_date,
    time_from,
    time_to=None,
    notes=None,
    user_id=None,
):
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            before = _task_snapshot(connection, epizod_element_id)
            if before is None:
                raise ValueError("Nie znaleziono zadania elementu.")
            if not _is_plannable_episode_element(before):
                raise ValueError(
                    "Ręczne planowanie dotyczy konsultacji i badań obrazowych."
                )
            planned_at = _combined_plan_datetime(plan_date, time_from)
            if planned_at is None:
                raise ValueError("Podaj datę oraz godzinę rozpoczęcia.")
            operation = (
                "ZMIANA_TERMINU_ELEMENTU"
                if before.get("data_zaplanowana")
                or before.get("kompas_plan_data")
                else "PLANOWANIE_ELEMENTU"
            )
            connection.execute(
                """
                UPDATE pk_zadania
                SET data_zaplanowana = ?,
                    kompas_plan_data = ?,
                    kompas_plan_godz_od = ?,
                    kompas_plan_godz_do = ?,
                    kompas_plan_uwagi = ?,
                    kompas_plan_user_id = ?,
                    kompas_plan_created_at = COALESCE(
                        kompas_plan_created_at,
                        CURRENT_TIMESTAMP
                    ),
                    kompas_plan_updated_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE zadanie_id = ?
                """,
                (
                    planned_at,
                    str(plan_date)[:10],
                    str(time_from)[:5],
                    str(time_to)[:5] if time_to else None,
                    str(notes or "").strip() or None,
                    _user_id(user_id),
                    before["zadanie_id"],
                ),
            )
            after = _task_snapshot(connection, epizod_element_id)
            record_history(
                connection,
                epizod_element_id,
                operation,
                before={"zadanie": before},
                after={"zadanie": after},
                reason="Ręczne zaplanowanie terminu w KOMPAS.",
                user_id=user_id,
            )
            return after


def clear_episode_element_plan(epizod_element_id, user_id=None):
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            before = _task_snapshot(connection, epizod_element_id)
            if before is None:
                raise ValueError("Nie znaleziono zadania elementu.")
            if not _is_plannable_episode_element(before):
                raise ValueError(
                    "Usuwanie terminu dotyczy konsultacji i badań obrazowych."
                )
            connection.execute(
                """
                UPDATE pk_zadania
                SET data_zaplanowana = NULL,
                    kompas_plan_data = NULL,
                    kompas_plan_godz_od = NULL,
                    kompas_plan_godz_do = NULL,
                    kompas_plan_uwagi = NULL,
                    kompas_plan_user_id = NULL,
                    kompas_plan_updated_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE zadanie_id = ?
                """,
                (before["zadanie_id"],),
            )
            after = _task_snapshot(connection, epizod_element_id)
            record_history(
                connection,
                epizod_element_id,
                "USUNIECIE_TERMINU_ELEMENTU",
                before={"zadanie": before},
                after={"zadanie": after},
                reason="Usunięcie terminu zaplanowanego w KOMPAS.",
                user_id=user_id,
            )
            return after


def _blocking_realization(connection, epizod_element_id):
    rows = connection.execute(
        """
        SELECT
            z.zadanie_id,
            z.status,
            z.data_realizacji,
            z.eskulap_system,
            z.eskulap_id,
            k.kod AS klocek_kod
        FROM pk_zadania z
        JOIN pk_epizod_elementy ee
            ON ee.epizod_element_id = z.epizod_element_id
        JOIN pk_klocki k
            ON k.klocek_id = ee.klocek_id
        WHERE z.epizod_element_id = ?
          AND (
              UPPER(z.status) IN ('ZAKONCZONE', 'ZAKOŃCZONE', 'ZREALIZOWANO', 'ZREALIZOWANE')
              OR z.data_realizacji IS NOT NULL
              OR z.eskulap_id IS NOT NULL
          )
        ORDER BY z.zadanie_id
        """,
        (epizod_element_id,),
    ).fetchall()
    for row in rows:
        if _is_invalid_specialist_consultation_assignment(row):
            continue
        return row
    return None


def can_deactivate_element(epizod_element_id) -> dict:
    initialize_database()
    with closing(create_connection()) as connection:
        element = _element_snapshot(connection, epizod_element_id)
        if element is None:
            return {"allowed": False, "reason": "Nie znaleziono elementu epizodu."}
        blocking = _blocking_realization(connection, epizod_element_id)
        if blocking is not None:
            return {
                "allowed": False,
                "reason": "Element ma zrealizowane albo potwierdzone zadanie.",
            }
        return {"allowed": True, "reason": ""}


def _cancel_open_tasks(connection, epizod_element_id, reason):
    rows = connection.execute(
        """
        SELECT zadanie_id, status, uwagi
        FROM pk_zadania
        WHERE epizod_element_id = ?
        """,
        (epizod_element_id,),
    ).fetchall()
    for row in rows:
        if _status(row["status"]) in TERMINAL_TASK_STATUSES:
            continue
        note = str(row["uwagi"] or "").strip()
        suffix = f"Powód anulowania: {reason}".strip()
        updated_note = f"{note}\n{suffix}".strip() if note else suffix
        connection.execute(
            """
            UPDATE pk_zadania
            SET status = 'ANULOWANE',
                uwagi = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE zadanie_id = ?
            """,
            (updated_note, row["zadanie_id"]),
        )


def deactivate_element(epizod_element_id, reason, user_id):
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            _deactivate_element(connection, epizod_element_id, reason, user_id)


def _deactivate_element(connection, epizod_element_id, reason, user_id):
    before = _element_snapshot(connection, epizod_element_id)
    if before is None:
        raise ValueError("Nie znaleziono elementu epizodu")
    if _blocking_realization(connection, epizod_element_id) is not None:
        raise ValueError(
            "Nie można dezaktywować elementu zrealizowanego lub potwierdzonego w Eskulapie."
        )
    connection.execute(
        """
        UPDATE pk_epizod_elementy
        SET czy_aktywny = 0,
            powod_modyfikacji = ?,
            updated_at = CURRENT_TIMESTAMP,
            updated_by = ?
        WHERE epizod_element_id = ?
        """,
        (reason, _user_id(user_id), epizod_element_id),
    )
    _cancel_open_tasks(connection, epizod_element_id, reason)
    after = _element_snapshot(connection, epizod_element_id)
    record_history(
        connection,
        epizod_element_id,
        "DEZAKTYWACJA",
        before=before,
        after=after,
        reason=reason,
        user_id=user_id,
    )
    _renumber_active_elements(connection, before["epizod_id"])


def reactivate_element(epizod_element_id, reason, user_id):
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            _reactivate_element(connection, epizod_element_id, reason, user_id)


def _reactivate_element(connection, epizod_element_id, reason, user_id):
    before = _element_snapshot(connection, epizod_element_id)
    if before is None:
        raise ValueError("Nie znaleziono elementu epizodu")
    connection.execute(
        """
        UPDATE pk_epizod_elementy
        SET czy_aktywny = 1,
            powod_modyfikacji = ?,
            updated_at = CURRENT_TIMESTAMP,
            updated_by = ?
        WHERE epizod_element_id = ?
        """,
        (reason, _user_id(user_id), epizod_element_id),
    )
    after = _element_snapshot(connection, epizod_element_id)
    record_history(
        connection,
        epizod_element_id,
        "REAKTYWACJA",
        before=before,
        after=after,
        reason=reason,
        user_id=user_id,
    )
    _renumber_active_elements(connection, before["epizod_id"])


def _max_completed_lp(connection, epizod_id):
    row = connection.execute(
        """
        SELECT MAX(ee.lp) AS max_lp
        FROM pk_epizod_elementy ee
        JOIN pk_zadania z
            ON z.epizod_element_id = ee.epizod_element_id
        WHERE ee.epizod_id = ?
          AND (
              UPPER(z.status) IN ('ZAKONCZONE', 'ZAKOŃCZONE', 'ZREALIZOWANO', 'ZREALIZOWANE')
              OR z.data_realizacji IS NOT NULL
          )
        """,
        (epizod_id,),
    ).fetchone()
    return row["max_lp"] if row else None


def duplicate_element(epizod_element_id, values, reason, user_id):
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            return _duplicate_element(
                connection,
                epizod_element_id,
                values,
                reason,
                user_id,
            )


def _duplicate_element(connection, epizod_element_id, values, reason, user_id):
    source = _element_snapshot(connection, epizod_element_id)
    if source is None:
        raise ValueError("Nie znaleziono elementu epizodu")
    insert_lp = int(values.get("lp") or int(source["lp"] or 0) + 1)
    completed_lp = _max_completed_lp(connection, source["epizod_id"])
    if completed_lp is not None and insert_lp <= int(completed_lp):
        raise ValueError(
            "Nie można wstawić elementu przed zrealizowaną częścią procesu."
        )

    cursor = connection.execute(
        """
        INSERT INTO pk_epizod_elementy(
            epizod_id,
            sciezka_element_id,
            klocek_id,
            element_zrodlowy_id,
            nazwa,
            lp,
            min_liczba,
            max_liczba,
            termin_liczba,
            jednostka_czasu_id,
            termin_od_epizod_element_id,
            czy_wymagany,
            czy_wymaga_zlecenia,
            czy_aktywny,
            typ_pochodzenia,
            powod_modyfikacji,
            created_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'POWIELENIE', ?, ?)
        """,
        (
            source["epizod_id"],
            source["sciezka_element_id"],
            source["klocek_id"],
            epizod_element_id,
            values.get("nazwa") or source["nazwa"],
            insert_lp,
            values.get("min_liczba", 1),
            values.get("max_liczba", 1),
            values.get("termin_liczba", source["termin_liczba"]),
            values.get("jednostka_czasu_id", source["jednostka_czasu_id"]),
            values.get(
                "termin_od_epizod_element_id",
                source["termin_od_epizod_element_id"],
            ),
            values.get("czy_wymagany", source["czy_wymagany"]),
            values.get(
                "czy_wymaga_zlecenia",
                source["czy_wymaga_zlecenia"],
            ),
            reason,
            _user_id(user_id),
        ),
    )
    new_id = int(cursor.lastrowid)
    _renumber_active_elements(connection, source["epizod_id"])
    after = _element_snapshot(connection, new_id)
    record_history(
        connection,
        new_id,
        "POWIELENIE",
        before=source,
        after=after,
        reason=reason,
        user_id=user_id,
    )
    return new_id


def reorder_episode_elements(epizod_id, ordered_ids) -> None:
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            ids = [int(value) for value in ordered_ids]
            completed_lp = _max_completed_lp(connection, epizod_id)
            if completed_lp is not None:
                completed_ids = [
                    int(row["epizod_element_id"])
                    for row in connection.execute(
                        """
                        SELECT DISTINCT ee.epizod_element_id
                        FROM pk_epizod_elementy ee
                        JOIN pk_zadania z
                            ON z.epizod_element_id = ee.epizod_element_id
                        WHERE ee.epizod_id = ?
                          AND (
                              UPPER(z.status) IN ('ZAKONCZONE', 'ZAKOŃCZONE', 'ZREALIZOWANO', 'ZREALIZOWANE')
                              OR z.data_realizacji IS NOT NULL
                          )
                        ORDER BY ee.lp, ee.epizod_element_id
                        """,
                        (epizod_id,),
                    ).fetchall()
                ]
                if ids[: len(completed_ids)] != completed_ids:
                    raise ValueError(
                        "Nie można naruszyć zrealizowanej części procesu."
                    )
            for lp, element_id in enumerate(ids, start=1):
                connection.execute(
                    """
                    UPDATE pk_epizod_elementy
                    SET lp = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE epizod_id = ?
                      AND epizod_element_id = ?
                    """,
                    (lp, epizod_id, element_id),
                )


def _renumber_active_elements(connection, epizod_id):
    rows = connection.execute(
        """
        SELECT epizod_element_id
        FROM pk_epizod_elementy
        WHERE epizod_id = ?
          AND czy_aktywny = 1
        ORDER BY lp, epizod_element_id
        """,
        (epizod_id,),
    ).fetchall()
    for lp, row in enumerate(rows, start=1):
        connection.execute(
            """
            UPDATE pk_epizod_elementy
            SET lp = ?
            WHERE epizod_element_id = ?
            """,
            (lp, row["epizod_element_id"]),
        )


def list_element_dependents(epizod_element_id) -> list[dict]:
    initialize_database()
    with closing(create_connection()) as connection:
        rows = connection.execute(
            """
            SELECT
                epizod_element_id,
                nazwa,
                lp,
                czy_aktywny
            FROM pk_epizod_elementy
            WHERE termin_od_epizod_element_id = ?
            ORDER BY lp, epizod_element_id
            """,
            (epizod_element_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_element_history(epizod_element_id) -> list[dict]:
    initialize_database()
    with closing(create_connection()) as connection:
        rows = connection.execute(
            """
            SELECT
                historia_id,
                epizod_element_id,
                epizod_id,
                operacja,
                dane_przed,
                dane_po,
                powod,
                changed_at,
                changed_by
            FROM pk_epizod_elementy_historia
            WHERE epizod_element_id = ?
            ORDER BY changed_at DESC, historia_id DESC
            """,
            (epizod_element_id,),
        ).fetchall()
    return [dict(row) for row in rows]
