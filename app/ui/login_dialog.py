from dataclasses import replace

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from app.services.auth_service import change_password, login
from version import APP_NAME


class MandatoryPasswordChangeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Zmiana hasła")
        self.resize(430, 220)

        layout = QVBoxLayout(self)
        message = QLabel(
            "Hasło startowe musi zostać zmienione przed uruchomieniem aplikacji."
        )
        message.setWordWrap(True)
        layout.addWidget(message)

        form = QFormLayout()
        self.password_edit = QLineEdit()
        self.confirm_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Nowe hasło:", self.password_edit)
        form.addRow("Powtórz hasło:", self.confirm_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        if self.password_edit.text() != self.confirm_edit.text():
            QMessageBox.warning(self, APP_NAME, "Podane hasła nie są identyczne.")
            return
        if len(self.password_edit.text()) < 8:
            QMessageBox.warning(
                self,
                APP_NAME,
                "Nowe hasło musi mieć co najmniej 8 znaków.",
            )
            return
        super().accept()

    def new_password(self):
        return self.password_edit.text()


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.authenticated_user = None
        self.setWindowTitle(f"{APP_NAME} — Logowanie")
        self.resize(430, 220)

        layout = QVBoxLayout(self)
        title = QLabel(APP_NAME)
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        form = QFormLayout()
        self.login_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Login:", self.login_edit)
        form.addRow("Hasło:", self.password_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Zaloguj")
        buttons.accepted.connect(self.authenticate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.login_edit.returnPressed.connect(self.password_edit.setFocus)
        self.password_edit.returnPressed.connect(self.authenticate)
        self.login_edit.setFocus()

    def authenticate(self):
        old_password = self.password_edit.text()
        try:
            user = login(self.login_edit.text(), old_password)
            if user.must_change_password:
                dialog = MandatoryPasswordChangeDialog(self)
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    return
                change_password(
                    user.user_id,
                    old_password,
                    dialog.new_password(),
                )
                user = replace(user, must_change_password=False)
            self.authenticated_user = user
            self.password_edit.clear()
            super().accept()
        except Exception as exc:
            self.password_edit.clear()
            QMessageBox.warning(self, APP_NAME, str(exc))
