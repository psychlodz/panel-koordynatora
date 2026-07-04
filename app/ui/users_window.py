from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
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

from app.services.auth_service import (
    block_user,
    create_user,
    list_roles,
    list_users,
    reset_password,
    set_user_roles,
    unblock_user,
)
from app.ui.ui_helpers import create_help_button, polish_dialog_buttons
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
            QMessageBox.warning(self, APP_NAME, "Podane hasła nie są identyczne.")
            return
        if len(self.password_edit.text()) < 8:
            QMessageBox.warning(
                self, APP_NAME, "Hasło musi mieć co najmniej 8 znaków."
            )
            return
        super().accept()

    def password(self):
        return self.password_edit.text()


class RolesWidget(QWidget):
    def __init__(self, selected=None, parent=None):
        super().__init__(parent)
        selected = {str(code).upper() for code in (selected or [])}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.checkboxes = {}
        for role in list_roles():
            checkbox = QCheckBox(f"{role['code']} — {role['name']}")
            checkbox.setChecked(role["code"].upper() in selected)
            self.checkboxes[role["code"].upper()] = checkbox
            layout.addWidget(checkbox)

    def selected_roles(self):
        return [
            code
            for code, checkbox in self.checkboxes.items()
            if checkbox.isChecked()
        ]


class AddUserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Nowy użytkownik")
        self.resize(500, 430)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.login_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.confirm_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.roles_widget = RolesWidget()
        form.addRow("Login:", self.login_edit)
        form.addRow("Imię i nazwisko:", self.name_edit)
        form.addRow("Hasło startowe:", self.password_edit)
        form.addRow("Powtórz hasło:", self.confirm_edit)
        form.addRow("Role:", self.roles_widget)
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
        if not self.login_edit.text().strip():
            QMessageBox.warning(self, APP_NAME, "Login jest wymagany.")
            return
        if not self.name_edit.text().strip():
            QMessageBox.warning(
                self, APP_NAME, "Imię i nazwisko jest wymagane."
            )
            return
        if self.password_edit.text() != self.confirm_edit.text():
            QMessageBox.warning(self, APP_NAME, "Podane hasła nie są identyczne.")
            return
        if len(self.password_edit.text()) < 8:
            QMessageBox.warning(
                self, APP_NAME, "Hasło musi mieć co najmniej 8 znaków."
            )
            return
        if not self.roles_widget.selected_roles():
            QMessageBox.warning(self, APP_NAME, "Wybierz co najmniej jedną rolę.")
            return
        super().accept()

    def values(self):
        return {
            "login": self.login_edit.text().strip(),
            "full_name": self.name_edit.text().strip(),
            "password": self.password_edit.text(),
            "role_codes": self.roles_widget.selected_roles(),
        }


class RoleDialog(QDialog):
    def __init__(self, selected_roles, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Role użytkownika")
        layout = QVBoxLayout(self)
        self.roles_widget = RolesWidget(selected_roles)
        layout.addWidget(self.roles_widget)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        polish_dialog_buttons(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        if not self.roles_widget.selected_roles():
            QMessageBox.warning(self, APP_NAME, "Wybierz co najmniej jedną rolę.")
            return
        super().accept()


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
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [
                "Login",
                "Imię i nazwisko",
                "Role",
                "Aktywny",
                "Zablokowany",
                "Zmiana hasła",
                "Błędne logowania",
            ]
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        self.add_button = QPushButton("Dodaj użytkownika")
        self.reset_button = QPushButton("Resetuj hasło")
        self.block_button = QPushButton("Zablokuj / odblokuj")
        self.roles_button = QPushButton("Przypisz role")
        self.units_button = QPushButton("Jednostki")
        self.refresh_button = QPushButton("Odśwież")
        self.help_button = create_help_button(
            self,
            "Użytkownicy",
            "To okno służy administratorowi do zarządzania kontami KOMPAS.\n\n"
            "Możesz dodawać użytkowników, resetować hasła, blokować konta "
            "i przypisywać role.\n\n"
            "Nie udostępniaj haseł ani uprawnień administracyjnych osobom "
            "nieupoważnionym.",
        )
        self.add_button.setToolTip("Dodaj nowe konto użytkownika.")
        self.reset_button.setToolTip(
            "Ustaw nowe hasło dla zaznaczonego użytkownika."
        )
        self.block_button.setToolTip(
            "Zablokuj albo odblokuj zaznaczone konto."
        )
        self.roles_button.setToolTip(
            "Przypisz role zaznaczonemu użytkownikowi."
        )
        self.units_button.setToolTip(
            "Przypisz jednostki organizacyjne zaznaczonemu użytkownikowi."
        )
        self.refresh_button.setToolTip(
            "Pobierz ponownie listę użytkowników."
        )
        for button in (
            self.add_button,
            self.reset_button,
            self.block_button,
            self.roles_button,
            self.units_button,
            self.refresh_button,
            self.help_button,
        ):
            actions.addWidget(button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.add_button.clicked.connect(self.add_user)
        self.reset_button.clicked.connect(self.reset_user_password)
        self.block_button.clicked.connect(self.toggle_user_block)
        self.roles_button.clicked.connect(self.assign_roles)
        self.units_button.clicked.connect(self.assign_units)
        self.refresh_button.clicked.connect(self.refresh_users)
        self.refresh_users()

    def selected_user_id(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def selected_user(self):
        user_id = self.selected_user_id()
        if user_id is None:
            QMessageBox.information(self, APP_NAME, "Wybierz użytkownika.")
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
                    "Wymagana" if user["must_change_password"] else "Nie",
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
                self, APP_NAME, f"Nie udało się pobrać użytkowników:\n\n{exc}"
            )

    def add_user(self):
        dialog = AddUserDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            create_user(self.current_user.user_id, **dialog.values())
            self.refresh_users()
        except Exception as exc:
            QMessageBox.critical(
                self, APP_NAME, f"Nie udało się dodać użytkownika:\n\n{exc}"
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
                self, APP_NAME, f"Nie udało się zresetować hasła:\n\n{exc}"
            )

    def toggle_user_block(self):
        user = self.selected_user()
        if user is None:
            return
        if user["user_id"] == self.current_user.user_id:
            QMessageBox.warning(
                self, APP_NAME, "Nie można zablokować własnego konta."
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
                f"Nie udało się zmienić blokady użytkownika:\n\n{exc}",
            )

    def assign_roles(self):
        user = self.selected_user()
        if user is None:
            return
        selected = [
            role.strip()
            for role in str(user["roles"] or "").split(",")
            if role.strip()
        ]
        dialog = RoleDialog(selected, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            set_user_roles(
                self.current_user.user_id,
                user["user_id"],
                dialog.roles_widget.selected_roles(),
            )
            self.refresh_users()
        except Exception as exc:
            QMessageBox.critical(
                self, APP_NAME, f"Nie udało się przypisać ról:\n\n{exc}"
            )

    def assign_units(self):
        user = self.selected_user()
        if user is None:
            return
        try:
            from app.ui.unit_assignments_dialog import UnitAssignmentsDialog

            dialog = UnitAssignmentsDialog(
                "user",
                user["user_id"],
                self,
            )
            dialog.exec()
        except Exception as exc:
            QMessageBox.critical(
                self,
                APP_NAME,
                f"Nie udało się otworzyć jednostek użytkownika:\n\n{exc}",
            )
