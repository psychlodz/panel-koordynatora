from contextlib import closing

from config import load_config
from db import create_connection


VISIT_PARAMETERS_VIEW = "ESK_RAPORTY.V_KOMPAS_PARAMETRY_WIZYT"


def list_visit_parameters(only_active=True) -> list[dict]:
    conditions = []
    parameters = {}
    if only_active:
        conditions.append(
            "UPPER(TRIM(NVL(p.CZY_AKTUALNE, 'T'))) "
            "IN ('T', 'TAK', 'Y', 'YES', '1')"
        )
    where_clause = (
        "WHERE " + " AND ".join(conditions)
        if conditions
        else ""
    )
    config = load_config()
    with closing(
        create_connection(
            config.database_user,
            config.database_password,
            config.database_dsn,
        )
    ) as connection:
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                f"""
                SELECT
                    p.PARAMETR_KOD,
                    p.PARAMETR_NAZWA,
                    p.CZY_AKTUALNE
                FROM {VISIT_PARAMETERS_VIEW} p
                {where_clause}
                ORDER BY p.PARAMETR_NAZWA, p.PARAMETR_KOD
                """,
                parameters,
            )
            columns = [
                column[0].lower()
                for column in cursor.description
            ]
            return [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]


__all__ = ["VISIT_PARAMETERS_VIEW", "list_visit_parameters"]
