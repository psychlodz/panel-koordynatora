import sys

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from app.ui.login_dialog import LoginDialog
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme
from version import APP_NAME, VERSION


def main():
    application = QApplication(sys.argv)
    application.setApplicationName(APP_NAME)
    application.setApplicationVersion(VERSION)
    apply_theme(application)

    login_dialog = LoginDialog()
    if login_dialog.exec() != QDialog.DialogCode.Accepted:
        return 0

    window = MainWindow(login_dialog.authenticated_user)
    window.show()
    return application.exec()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        application = QApplication.instance()
        if application is not None:
            QMessageBox.critical(
                None,
                APP_NAME,
                f"Nie udało się uruchomić aplikacji:\n\n{exc}",
            )
        raise
