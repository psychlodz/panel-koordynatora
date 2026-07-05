from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.repositories.user_unit_repository import list_user_units
from app.services.auth_service import (
    block_user,
    create_user,
    list_users,
    reset_password,
    unblock_user,
    update_user,
)
from app.ui.login_dialog import _add_password_toggle
from app.ui.ui_helpers import create_help_button, polish_dialog_buttons
from app.ui.user_editor_dialog import UserEditorDialog
from version import APP_NAME


class PasswordDialog(QDialog):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.password_edit = QLineEdit()
        self.confirm_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_toggle = _add_password_toggle(self.password_edit)
        self.confirm_toggle = _add_password_toggle(self.confirm_edit)
        form.addRow("Nowe hasło:", self.password_edit)
        form.addRow("Powtórz hasło:", self.confirm_edit)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        polish_dialog_buttons(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        if self.password_edit.text() != self.confirm_edit.text():
            QMessageBox.warning(
                self,
                APP_NAME,
                "Podane hasła nie są identyczne.",
            )
            return
        if len(self.password_edit.text()) < 8:
            QMessageBox.warning(
                self,
                APP_NAME,
                "Hasło musi mieć co najmniej 8 znaków.",
            )
            return
        super().accept()

    def password(self):
        return self.password_edit.text()


class UsersWindow(QWidget):
    def __init__(self, current_user, parent=None):
        if not current_user or not current_user.is_admin:
            raise PermissionError("Dostęp wymaga roli ADMIN")
        super().__init__(parent)
        self.current_user = current_user
        self._users = {}
        self.setWindowTitle(f"{APP_NAME} — Użytkownicy")
        self.resize(1050, 600)

        layout = QVBoxLayout(self)
        title = QLabel("Użytkownicy KOMPAS")
        title.setObjectName("windowTitle")
        layout.addWidget(title)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            [
                "Login",
                "Imię i nazwisko",
                "Role",
                "Aktywny",
                "Zablokowany",
                "Błędne logowania",
            ]
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        self.add_button = QPushButton("Dodaj użytkownika")
        self.edit_button = QPushButton("Edytuj użytkownika")
        self.reset_button = QPushButton("Resetuj hasło")
        self.block_button = QPushButton("Zablokuj / odblokuj")
        self.refresh_button = QPushButton("Odśwież")
        self.help_button = create_help_button(
            self,
            "Użytkownicy",
            "To okno służy administratorowi do zarządzania kontami KOMPAS.\n\n"
            "W formularzu dodawania i edycji możesz ustawić dane konta, role "
            "oraz jednostki organizacyjne pobrane z Eskulapa.\n\n"
            "Nie udostępniaj haseł ani uprawnień administracyjnych osobom "
            "nieupoważnionym.",
        )
        self.add_button.setToolTip(
            "Dodaj konto wraz z rolami i jednostkami organizacyjnymi."
        )
        self.edit_button.setToolTip(
            "Edytuj dane, role i jednostki zaznaczonego użytkownika."
        )
        self.reset_button.setToolTip(
            "Ustaw nowe hasło dla zaznaczonego użytkownika."
        )
        self.block_button.setToolTip(
            "Zablokuj albo odblokuj zaznaczone konto."
        )
        self.refresh_button.setToolTip(
            "Pobierz ponownie listę użytkowników."
        )
        for button in (
            self.add_button,
            self.edit_button,
            self.reset_button,
            self.block_button,
            self.refresh_button,
            self.help_button,
        ):
            actions.addWidget(button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.add_button.clicked.connect(self.add_user)
        self.edit_button.clicked.connect(self.edit_user)
        self.reset_button.clicked.connect(self.reset_user_password)
        self.block_button.clicked.connect(self.toggle_user_block)
        self.refresh_button.clicked.connect(self.refresh_users)
        self.table.itemDoubleClicked.connect(self.edit_user)
        self.refresh_users()

    def selected_user_id(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def selected_user(self):
        user_id = self.selected_user_id()
        if user_id is None:
            QMessageBox.information(
                self,
                APP_NAME,
                "Wybierz użytkownika.",
            )
            return None
        return self._users.get(user_id)

    def refresh_users(self):
        try:
            users = list_users(self.current_user.user_id)
            self._users = {user["user_id"]: user for user in users}
            self.table.setRowCount(len(users))
            for row_index, user in enumerate(users):
                values = [
                    user["login"],
                    user["full_name"],
                    user["roles"],
                    "Tak" if user["is_active"] else "Nie",
                    user["locked_at"] or "",
                    user["failed_login_count"],
                ]
                for column_index, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    if column_index == 0:
                        item.setData(
                            Qt.ItemDataRole.UserRole,
                            user["user_id"],
                        )
                    self.table.setItem(row_index, column_index, item)
        except Exception as exc:
            QMessageBox.critical(
                self,
                APP_NAME,
                f"Nie udało się pobrać użytkowników:\n\n{exc}",
            )

    def add_user(self):
        dialog = UserEditorDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            create_user(
                self.current_user.user_id,
                **dialog.values(),
            )
            self.refresh_users()
        except Exception as exc:
            QMessageBox.critical(
                self,
                APP_NAME,
                f"Nie udało się dodać użytkownika:\n\n{exc}",
            )

    def edit_user(self, *_args):
        user = self.selected_user()
        if user is None:
            return
        try:
            assigned_units = list_user_units(user["user_id"])
            default_unit = next(
                (
                    unit["jo_id"]
                    for unit in assigned_units
                    if unit["is_default"]
                ),
                None,
            )
            dialog = UserEditorDialog(
                user=user,
                assigned_units=assigned_units,
                default_unit_id=default_unit,
                parent=self,
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            update_user(
                self.current_user.user_id,
                user["user_id"],
                **dialog.values(),
            )
            self.refresh_users()
        except Exception as exc:
            QMessageBox.critical(
                self,
                APP_NAME,
                f"Nie udało się edytować użytkownika:\n\n{exc}",
            )

    def reset_user_password(self):
        user = self.selected_user()
        if user is None:
            return
        dialog = PasswordDialog(f"{APP_NAME} — Reset hasła", self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            reset_password(
                self.current_user.user_id,
                user["user_id"],
                dialog.password(),
            )
            self.refresh_users()
        except Exception as exc:
            QMessageBox.critical(
                self,
                APP_NAME,
                f"Nie udało się zresetować hasła:\n\n{exc}",
            )

    def toggle_user_block(self):
        user = self.selected_user()
        if user is None:
            return
        if user["user_id"] == self.current_user.user_id:
            QMessageBox.warning(
                self,
                APP_NAME,
                "Nie można zablokować własnego konta.",
            )
            return
        try:
            if user["is_active"] and not user["locked_at"]:
                block_user(user["user_id"])
            else:
                unblock_user(user["user_id"])
            self.refresh_users()
        except Exception as exc:
            QMessageBox.critical(
                self,
                APP_NAME,
                "Nie udało się zmienić blokady użytkownika:\n\n"
                f"{exc}",
            )
