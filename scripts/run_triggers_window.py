import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication, QMessageBox

from app.repositories.pathway_repository import (
    list_pathway_elements,
    list_pathways,
)
from app.repositories.program_repository import list_programs
from app.ui.triggers_window import TriggersWindow


def main():
    application = QApplication(sys.argv)
    application.setApplicationName("KOMPAS")

    programs = list_programs()
    program = next(
        (item for item in programs if item["kod"] == "ADHD_DZ_ML"),
        programs[0] if programs else None,
    )
    pathways = list_pathways(program["program_id"]) if program else []
    pathway = next(
        (item for item in pathways if item["kod"] == "PODSTAWOWA"),
        pathways[0] if pathways else None,
    )
    elements = (
        list_pathway_elements(pathway["sciezka_id"])
        if pathway
        else []
    )
    if not elements:
        QMessageBox.critical(
            None,
            "KOMPAS",
            "Brak elementu, dla którego można otworzyć wyzwalacze.",
        )
        return 1

    window = TriggersWindow(elements[0])
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
