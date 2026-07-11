import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.repositories.visit_mapping_repository import get_block_for_visit_parameter
from app.repositories.visit_type_dictionary_repository import (
    get_by_code,
    get_sync_summary,
)
from app.services.visit_type_dictionary_sync_service import (
    synchronize_visit_type_dictionary,
)


def main():
    summary = synchronize_visit_type_dictionary()
    print("Synchronizacja słownika rodzajów wizyt:")
    for key, value in summary.items():
        print(f"- {key}: {value}")

    f18 = get_by_code("F18")
    if not f18:
        raise AssertionError("Brak rodzaju wizyty F18 w lokalnym słowniku")

    mapping = get_block_for_visit_parameter("F18")
    if not mapping or mapping.get("kod") != "PKK_KWAL":
        raise AssertionError("F18 nie jest aktywnie zmapowany na PKK_KWAL")

    db_summary = get_sync_summary()
    print("Podsumowanie lokalnego słownika:")
    for key, value in db_summary.items():
        print(f"- {key}: {value}")
    print("F18 -> PKK_KWAL: OK")


if __name__ == "__main__":
    main()
