import logging
from contextlib import closing
from datetime import datetime

from app.repositories.db_connection import (
    create_connection,
    initialize_database,
    patient_id_column,
)


TASK_STATUS_PENDING = "DO_ZAPLANOWANIA"
TASK_STATUS_COMPLETED = "ZAKONCZONE"
logger = logging.getLogger(__name__)


def _validate_episode_data(connection, pacjent_id, program_id, sciezka_id):
    if not str(pacjent_id).strip():
        raise ValueError("pacjent_id jest wymagany")

    pathway = connection.execute(
        """
        SELECT s.sciezka_id
        FROM pk_sciezki s
        JOIN pk_programy p ON p.program_id = s.program_id
        WHERE s.sciezka_id = ?
          AND s.program_id = ?
          AND s.czy_aktywna = 1
          AND p.czy_aktywny = 1
        """,
        (sciezka_id, program_id),
    ).fetchone()
    if pathway is None:
        raise ValueError(
            "Nie znaleziono aktywnej ścieżki dla wybranego programu"
        )


def _insert_task_if_missing(connection, epizod_id, element_id):
    existing = connection.execute(
        """
        SELECT zadanie_id
        FROM pk_zadania
        WHERE epizod_id = ?
          AND element_id = ?
        LIMIT 1
        """,
        (epizod_id, element_id),
    ).fetchone()
    if existing is not None:
        return None

    cursor = connection.execute(
        """
        INSERT INTO pk_zadania(
            epizod_id,
            element_id,
            status,
            zrodlo
        )
        VALUES (?, ?, ?, 'PROGRAM')
        """,
        (epizod_id, element_id, TASK_STATUS_PENDING),
    )
    return int(cursor.lastrowid)


def _activate_triggered_tasks(
    connection,
    epizod_id,
    trigger_type,
    trigger_element_id=None,
):
    episode = connection.execute(
        """
        SELECT sciezka_id
        FROM pk_epizody
        WHERE epizod_id = ?
        """,
        (epizod_id,),
    ).fetchone()
    if episode is None:
        raise ValueError(f"Nie znaleziono epizodu o ID {epizod_id}")

    elements = connection.execute(
        """
        SELECT DISTINCT e.element_id
        FROM pk_wyzwalacze w
        JOIN pk_sciezka_elementy e ON e.element_id = w.element_id
        WHERE e.sciezka_id = ?
          AND e.czy_aktywny = 1
          AND w.trigger_type = ?
          AND (
              (? IS NULL AND w.trigger_element_id IS NULL)
              OR w.trigger_element_id = ?
          )
        ORDER BY e.lp
        """,
        (
            episode["sciezka_id"],
            trigger_type,
            trigger_element_id,
            trigger_element_id,
        ),
    ).fetchall()

    task_ids = []
    for element in elements:
        task_id = _insert_task_if_missing(
            connection,
            epizod_id,
            element["element_id"],
        )
        if task_id is not None:
            task_ids.append(task_id)
    return task_ids


def create_episode_with_tasks(
    pacjent_id,
    program_id,
    sciezka_id,
    data_start,
    koordynator_id=None,
    uwagi=None,
    source_system=None,
    source_type=None,
    source_id=None,
) -> int:
    initialize_database()
    with closing(create_connection()) as connection:
        try:
            _validate_episode_data(
                connection,
                pacjent_id,
                program_id,
                sciezka_id,
            )
            patient_column = patient_id_column()
            cursor = connection.execute(
                f"""
                INSERT INTO pk_epizody(
                    {patient_column},
                    program_id,
                    sciezka_id,
                    data_start,
                    status,
                    koordynator_id,
                    uwagi,
                    source_system,
                    source_type,
                    source_id
                )
                VALUES (?, ?, ?, ?, 'NOWY', ?, ?, ?, ?, ?)
                """,
                (
                    str(pacjent_id).strip(),
                    program_id,
                    sciezka_id,
                    data_start,
                    koordynator_id,
                    uwagi,
                    source_system,
                    source_type,
                    str(source_id) if source_id is not None else None,
                ),
            )
            epizod_id = int(cursor.lastrowid)
            logger.debug("EPIZOD_CREATED epizod_id=%s", epizod_id)
            task_ids = _activate_triggered_tasks(
                connection,
                epizod_id,
                "START_EPIZODU",
            )
            logger.debug(
                "TASKS_CREATED epizod_id=%s count=%s ids=%s",
                epizod_id,
                len(task_ids),
                task_ids,
            )
            connection.commit()
            logger.debug("COMMIT_OK epizod_id=%s", epizod_id)
        except Exception:
            connection.rollback()
            logger.debug("ROLLBACK", exc_info=True)
            raise
    return epizod_id


def activate_next_tasks(
    epizod_id,
    trigger_element_id,
    trigger_type="PO_ZAKONCZENIU",
) -> list[int]:
    initialize_database()
    with closing(create_connection()) as connection:
        with connection:
            return _activate_triggered_tasks(
                connection,
                epizod_id,
                str(trigger_type).strip().upper(),
                trigger_element_id,
            )


def complete_task(
    zadanie_id,
    data_realizacji=None,
    completion_status=TASK_STATUS_COMPLETED,
    eskulap_system=None,
    eskulap_id=None,
) -> list[int]:
    initialize_database()
    completion_date = data_realizacji or datetime.now().isoformat(
        timespec="seconds"
    )

    with closing(create_connection()) as connection:
        with connection:
            task = connection.execute(
                """
                SELECT zadanie_id, epizod_id, element_id, status
                FROM pk_zadania
                WHERE zadanie_id = ?
                """,
                (zadanie_id,),
            ).fetchone()
            if task is None:
                raise ValueError(f"Nie znaleziono zadania o ID {zadanie_id}")
            if task["element_id"] is None:
                raise ValueError("Zadanie nie jest powiązane z elementem ścieżki")
            if task["status"] == TASK_STATUS_COMPLETED:
                return []

            connection.execute(
                """
                UPDATE pk_zadania
                SET status = ?,
                    data_realizacji = ?,
                    eskulap_system = COALESCE(?, eskulap_system),
                    eskulap_id = COALESCE(?, eskulap_id),
                    updated_at = CURRENT_TIMESTAMP
                WHERE zadanie_id = ?
                """,
                (
                    completion_status,
                    completion_date,
                    eskulap_system,
                    eskulap_id,
                    zadanie_id,
                ),
            )
            return _activate_triggered_tasks(
                connection,
                task["epizod_id"],
                "PO_ZAKONCZENIU",
                task["element_id"],
            )
