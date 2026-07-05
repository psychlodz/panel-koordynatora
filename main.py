import sys

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from app.ui.login_dialog import LoginDialog
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme
from app.services.work_context import initialize_work_context
from app.services.debug_logging import configure_debug_logging
from version import APP_NAME, VERSION


def main():
    configure_debug_logging()
    application = QApplication(sys.argv)
    application.setApplicationName(APP_NAME)
    application.setApplicationVersion(VERSION)
    apply_theme(application)

    login_dialog = LoginDialog()
    if login_dialog.exec() != QDialog.DialogCode.Accepted:
        return 0

    current_unit = initialize_work_context(
        login_dialog.authenticated_user
    )
    if current_unit is None:
        QMessageBox.warning(
            None,
            APP_NAME,
            "Użytkownik nie ma przypisanej jednostki organizacyjnej. "
            "Skontaktuj się z administratorem.",
        )

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
