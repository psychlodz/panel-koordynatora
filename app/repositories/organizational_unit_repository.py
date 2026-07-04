import re
from contextlib import closing

from config import load_config
from db import create_connection


SQL_IDENTIFIER = re.compile(r"^[A-Za-z0-9_$#.]+$")


def list_organizational_units(search_text=None) -> list[dict]:
    config = load_config()
    view_name = str(config.view_name or "").strip()
    if not SQL_IDENTIFIER.fullmatch(view_name):
        raise ValueError("Nieprawidłowa nazwa widoku jednostek w konfiguracji")

    conditions = ["jo_id IS NOT NULL"]
    parameters = {}
    search_text = str(search_text or "").strip()
    if search_text:
        conditions.append(
            """
            (
                UPPER(NVL(jo_symbol, '')) LIKE UPPER(:search_pattern)
                OR UPPER(NVL(jo_nazwa, '')) LIKE UPPER(:search_pattern)
                OR TO_CHAR(jo_id) LIKE :search_pattern
            )
            """
        )
        parameters["search_pattern"] = f"%{search_text}%"

    sql = f"""
        SELECT DISTINCT
            jo_id,
            jo_symbol,
            jo_nazwa
        FROM {view_name}
        WHERE {" AND ".join(conditions)}
        ORDER BY jo_symbol, jo_nazwa, jo_id
    """
    with closing(
        create_connection(
            config.database_user,
            config.database_password,
            config.database_dsn,
        )
    ) as connection:
        with closing(connection.cursor()) as cursor:
            cursor.execute(sql, parameters)
            columns = [column[0].lower() for column in cursor.description]
            return [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]
