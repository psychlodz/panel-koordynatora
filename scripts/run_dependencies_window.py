import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication, QMessageBox

from app.repositories.pathway_repository import list_pathways
from app.repositories.program_repository import list_programs
from app.ui.dependencies_window import DependenciesWindow


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
    if pathway is None:
        QMessageBox.critical(
            None,
            "KOMPAS",
            "Brak ścieżki, dla której można otworzyć zależności.",
        )
        return 1

    window = DependenciesWindow(pathway["sciezka_id"])
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
