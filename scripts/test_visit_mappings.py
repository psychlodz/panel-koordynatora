import sys
from contextlib import closing
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.repositories.db_connection import create_connection
from app.repositories.visit_mapping_repository import (
    VisitTypeMappingConflict,
    assign_visit_types,
    get_active_parameter_codes_for_block,
    get_block_for_visit_parameter,
    list_mapping_blocks,
    list_mappings_for_block,
    remove_mapping,
    replace_mapping,
)


TEST_CODES = ("TEST_MULTI_A", "TEST_MULTI_B")


def _cleanup_test_data(connection):
    rows = connection.execute(
        f"""
        SELECT rodzaj_wizyty_id
        FROM pk_rodzaje_wizyt_eskulap
        WHERE parametr_kod IN ({",".join("?" for _ in TEST_CODES)})
        """,
        TEST_CODES,
    ).fetchall()
    ids = [row["rodzaj_wizyty_id"] for row in rows]
    if not ids:
        return
    placeholders = ",".join("?" for _ in ids)
    connection.execute(
        f"""
        DELETE FROM pk_mapowanie_wizyt
        WHERE rodzaj_wizyty_id IN ({placeholders})
        """,
        tuple(ids),
    )
    connection.execute(
        f"""
        DELETE FROM pk_rodzaje_wizyt_eskulap
        WHERE rodzaj_wizyty_id IN ({placeholders})
        """,
        tuple(ids),
    )


def _create_test_visit_types(connection):
    ids = []
    for code in TEST_CODES:
        cursor = connection.execute(
            """
            INSERT INTO pk_rodzaje_wizyt_eskulap(
                parametr_kod,
                parametr_nazwa,
                czy_aktualny_eskulap,
                czy_aktywny_kompas
            )
            VALUES (?, ?, 1, 1)
            """,
            (code, f"Testowy rodzaj wizyty {code}"),
        )
        ids.append(int(cursor.lastrowid))
    return ids


def _active_visit_type_ids_for_block(klocek_id):
    return [
        int(row["rodzaj_wizyty_id"])
        for row in list_mappings_for_block(klocek_id)
    ]


def _test_many_visit_types_per_block():
    blocks = list_mapping_blocks(only_active=True)
    if len(blocks) < 2:
        raise AssertionError("Do testu mapowań wymagane są co najmniej dwa klocki")
    block_a = next(
        (block for block in blocks if block.get("kod") == "PKK_KWAL"),
        blocks[0],
    )
    block_b = next(
        block
        for block in blocks
        if int(block["klocek_id"]) != int(block_a["klocek_id"])
    )

    with closing(create_connection()) as connection:
        with connection:
            _cleanup_test_data(connection)
            visit_type_ids = _create_test_visit_types(connection)

    try:
        current_ids = _active_visit_type_ids_for_block(block_a["klocek_id"])
        summary = assign_visit_types(
            block_a["klocek_id"],
            current_ids + visit_type_ids,
        )
        assert summary["added"] == 2

        for code in TEST_CODES:
            mapping = get_block_for_visit_parameter(code)
            assert mapping is not None
            assert int(mapping["klocek_id"]) == int(block_a["klocek_id"])

        try:
            assign_visit_types(block_b["klocek_id"], [visit_type_ids[0]])
        except VisitTypeMappingConflict:
            pass
        else:
            raise AssertionError(
                "Ten sam rodzaj wizyty został aktywnie przypisany do dwóch klocków"
            )

        moved_mapping_id = replace_mapping(
            visit_type_ids[0],
            block_b["klocek_id"],
        )
        assert moved_mapping_id
        moved = get_block_for_visit_parameter(TEST_CODES[0])
        assert int(moved["klocek_id"]) == int(block_b["klocek_id"])

        remaining = get_block_for_visit_parameter(TEST_CODES[1])
        assert int(remaining["klocek_id"]) == int(block_a["klocek_id"])
        remove_mapping(remaining["mapowanie_id"])
        assert get_block_for_visit_parameter(TEST_CODES[0]) is not None
        assert get_block_for_visit_parameter(TEST_CODES[1]) is None
    finally:
        with closing(create_connection()) as connection:
            with connection:
                _cleanup_test_data(connection)


def main():
    with closing(create_connection()) as connection:
        missing_colors = connection.execute(
            """
            SELECT kod
            FROM pk_klocki
            WHERE czy_aktywny = 1
              AND (
                    kolor IS NULL
                    OR trim(kolor) = ''
                    OR kolor_tekstu IS NULL
                    OR trim(kolor_tekstu) = ''
              )
            ORDER BY kod
            """
        ).fetchall()
        assert not missing_colors, (
            "Aktywne klocki bez pełnej kolorystyki: "
            f"{[row['kod'] for row in missing_colors]}"
        )

    qualification_codes = get_active_parameter_codes_for_block("PKK_KWAL")
    assert "F18" in qualification_codes, (
        "Brak aktywnego mapowania PKK_KWAL → F18"
    )
    mapped_block = get_block_for_visit_parameter("F18")
    assert mapped_block is not None
    assert mapped_block["kod"] == "PKK_KWAL"

    _test_many_visit_types_per_block()

    print("Kolory aktywnych klocków: OK")
    print("Mapowanie PKK_KWAL -> F18 -> Wizyta kwalifikacyjna PKK: OK")
    print("Jeden klocek -> wiele rodzajów wizyt: OK")
    print("Jeden rodzaj wizyty -> jedno aktywne przypisanie: OK")


if __name__ == "__main__":
    main()
