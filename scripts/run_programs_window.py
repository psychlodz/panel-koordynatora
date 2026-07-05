import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication

from app.ui.programs_window import ProgramsWindow
from app.ui.theme import apply_theme


def main():
    application = QApplication(sys.argv)
    apply_theme(application)
    application.setApplicationName("KOMPAS")
    window = ProgramsWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
