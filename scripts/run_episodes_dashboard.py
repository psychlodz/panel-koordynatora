import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication

from app.ui.episodes_dashboard_window import EpisodesDashboardWindow
from app.ui.theme import apply_theme


def main():
    application = QApplication(sys.argv)
    apply_theme(application)
    application.setApplicationName("KOMPAS")
    window = EpisodesDashboardWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
