import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication

from app.ui.new_episode_wizard import EpisodeWizard


def main():
    application = QApplication(sys.argv)
    application.setApplicationName("KOMPAS")
    wizard = EpisodeWizard()
    wizard.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
