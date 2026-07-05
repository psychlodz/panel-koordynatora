import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication, QMessageBox

from app.repositories.program_repository import list_programs
from app.ui.pathways_window import PathwaysWindow
from app.ui.theme import apply_theme


def main():
    application = QApplication(sys.argv)
    apply_theme(application)
    application.setApplicationName("KOMPAS")

    programs = list_programs()
    program = next(
        (item for item in programs if item["kod"] == "ADHD_DZ_ML"),
        programs[0] if programs else None,
    )
    if program is None:
        QMessageBox.critical(
            None, "KOMPAS", "Brak programu, dla którego można otworzyć ścieżki."
        )
        return 1

    window = PathwaysWindow(program["program_id"])
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
