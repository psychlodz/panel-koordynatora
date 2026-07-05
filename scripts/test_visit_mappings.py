import sys
from contextlib import closing
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.repositories.db_connection import create_connection
from app.repositories.visit_mapping_repository import (
    get_active_parameter_codes_for_block,
    get_block_for_visit_parameter,
)


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

    print("Kolory aktywnych klocków: OK")
    print("Mapowanie PKK_KWAL -> F18 -> Wizyta kwalifikacyjna PKK: OK")


if __name__ == "__main__":
    main()
