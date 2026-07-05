from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
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

from app.gateway.eskulap_gateway import EskulapGateway
from app.services.auth_service import list_roles
from app.ui.login_dialog import _add_password_toggle
from app.ui.ui_helpers import polish_dialog_buttons
from app.ui.widgets.busy_indicator import busy_operation
from version import APP_NAME


def _unit_value(unit, field_name):
    if isinstance(unit, dict):
        return unit.get(field_name)
    return getattr(unit, field_name, None)


def _unit_dict(unit):
    jo_id = str(_unit_value(unit, "jo_id") or "").strip()
    return {
        "jo_id": jo_id,
        "jo_symbol": _unit_value(unit, "jo_symbol"),
        "jo_nazwa": _unit_value(unit, "jo_nazwa"),
    }


def _unit_label(unit):
    symbol = str(unit.get("jo_symbol") or "").strip()
    name = str(unit.get("jo_nazwa") or "").strip()
    description = " — ".join(value for value in (symbol, name) if value)
    return (
        f"{description} [{unit['jo_id']}]"
        if description
        else f"Jednostka [{unit['jo_id']}]"
    )


class RolesWidget(QWidget):
    def __init__(self, selected=None, parent=None):
        super().__init__(parent)
        selected = {str(code).upper() for code in (selected or [])}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.checkboxes = {}
        for role in list_roles():
            code = str(role["code"]).upper()
            checkbox = QCheckBox(f"{role['code']} — {role['name']}")
            checkbox.setChecked(code in selected)
            self.checkboxes[code] = checkbox
            layout.addWidget(checkbox)

    def selected_roles(self):
        return [
            code
            for code, checkbox in self.checkboxes.items()
            if checkbox.isChecked()
        ]


class OrganizationalUnitsWidget(QWidget):
    def __init__(
        self,
        assigned_units=None,
        default_unit_id=None,
        parent=None,
    ):
        super().__init__(parent)
        self.units = {}
        self.selection_order = []
        self.initial_default_id = (
            str(default_unit_id)
            if default_unit_id is not None
            else None
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        tools = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(
            "Filtruj po symbolu, nazwie lub identyfikatorze..."
        )
        self.refresh_button = QPushButton("Pobierz z Eskulapa")
        self.refresh_button.setToolTip(
            "Pobierz aktualną listę jednostek organizacyjnych z Eskulapa."
        )
        tools.addWidget(self.search_edit, 1)
        tools.addWidget(self.refresh_button)
        layout.addLayout(tools)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(
            ["Symbol", "Nazwa", "Identyfikator"]
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        layout.addWidget(self.table, 1)

        default_row = QHBoxLayout()
        default_row.addWidget(QLabel("Jednostka domyślna:"))
        self.default_combo = QComboBox()
        self.default_combo.setMinimumWidth(360)
        default_row.addWidget(self.default_combo, 1)
        layout.addLayout(default_row)

        for unit in assigned_units or []:
            normalized = _unit_dict(unit)
            unit_id = normalized["jo_id"]
            if not unit_id:
                continue
            self.units[unit_id] = normalized
            self.selection_order.append(unit_id)
        self._populate()

        self.search_edit.textChanged.connect(self.apply_filter)
        self.refresh_button.clicked.connect(self.load_units)
        self.table.itemChanged.connect(self._selection_changed)

    def load_units(self):
        try:
            with busy_operation(
                self.window(),
                "Trwa pobieranie jednostek organizacyjnych z Eskulapa...",
            ):
                units = EskulapGateway().list_organizational_units()
            for unit in units:
                normalized = _unit_dict(unit)
                if not normalized["jo_id"]:
                    continue
                self.units[normalized["jo_id"]] = normalized
            self._populate()
        except Exception as exc:
            QMessageBox.critical(
                self,
                APP_NAME,
                "Nie udało się pobrać jednostek z Eskulapa:\n\n"
                f"{exc}",
            )

    def _populate(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.units))
        for row_index, unit in enumerate(self.units.values()):
            symbol_item = QTableWidgetItem(
                str(unit.get("jo_symbol") or "")
            )
            symbol_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            symbol_item.setData(
                Qt.ItemDataRole.UserRole,
                unit["jo_id"],
            )
            symbol_item.setCheckState(
                Qt.CheckState.Checked
                if unit["jo_id"] in self.selection_order
                else Qt.CheckState.Unchecked
            )
            self.table.setItem(row_index, 0, symbol_item)
            self.table.setItem(
                row_index,
                1,
                QTableWidgetItem(str(unit.get("jo_nazwa") or "")),
            )
            self.table.setItem(
                row_index,
                2,
                QTableWidgetItem(unit["jo_id"]),
            )
        self.table.blockSignals(False)
        self._refresh_default_combo()
        self.apply_filter(self.search_edit.text())

    def _selection_changed(self, item):
        if item.column() != 0:
            return
        unit_id = str(item.data(Qt.ItemDataRole.UserRole))
        if item.checkState() == Qt.CheckState.Checked:
            if unit_id not in self.selection_order:
                self.selection_order.append(unit_id)
        else:
            self.selection_order = [
                selected_id
                for selected_id in self.selection_order
                if selected_id != unit_id
            ]
        self._refresh_default_combo()

    def _refresh_default_combo(self):
        current = self.default_combo.currentData()
        preferred = (
            str(current)
            if current is not None
            else self.initial_default_id
        )
        selected_ids = [
            unit_id
            for unit_id in self.selection_order
            if unit_id in self.units
        ]
        if preferred not in selected_ids:
            preferred = selected_ids[0] if selected_ids else None

        self.default_combo.blockSignals(True)
        self.default_combo.clear()
        for unit_id in selected_ids:
            self.default_combo.addItem(
                _unit_label(self.units[unit_id]),
                unit_id,
            )
        if preferred is not None:
            index = self.default_combo.findData(preferred)
            if index >= 0:
                self.default_combo.setCurrentIndex(index)
        self.default_combo.setEnabled(bool(selected_ids))
        self.default_combo.blockSignals(False)

    def apply_filter(self, search_text):
        pattern = str(search_text or "").strip().casefold()
        for row in range(self.table.rowCount()):
            values = [
                self.table.item(row, column).text()
                for column in range(self.table.columnCount())
            ]
            self.table.setRowHidden(
                row,
                bool(pattern)
                and not any(pattern in value.casefold() for value in values),
            )

    def selected_units(self):
        return [
            self.units[unit_id]
            for unit_id in self.selection_order
            if unit_id in self.units
        ]

    def default_unit_id(self):
        value = self.default_combo.currentData()
        return str(value) if value is not None else None


class UserEditorDialog(QDialog):
    def __init__(
        self,
        user=None,
        assigned_units=None,
        default_unit_id=None,
        parent=None,
    ):
        super().__init__(parent)
        self.user = user
        self.is_edit = user is not None
        self.setWindowTitle(
            f"{APP_NAME} — "
            + ("Edytuj użytkownika" if self.is_edit else "Nowy użytkownik")
        )
        self.resize(780, 720)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.login_edit = QLineEdit()
        self.name_edit = QLineEdit()
        if self.is_edit:
            self.login_edit.setText(str(user["login"]))
            self.name_edit.setText(str(user["full_name"]))
        form.addRow("Login:", self.login_edit)
        form.addRow("Imię i nazwisko:", self.name_edit)

        self.password_edit = None
        self.confirm_edit = None
        if not self.is_edit:
            self.password_edit = QLineEdit()
            self.confirm_edit = QLineEdit()
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.password_toggle = _add_password_toggle(self.password_edit)
            self.confirm_toggle = _add_password_toggle(self.confirm_edit)
            form.addRow("Hasło startowe:", self.password_edit)
            form.addRow("Powtórz hasło:", self.confirm_edit)

        selected_roles = []
        if self.is_edit:
            selected_roles = [
                role.strip()
                for role in str(user.get("roles") or "").split(",")
                if role.strip()
            ]
        self.roles_widget = RolesWidget(selected_roles)
        form.addRow("Role:", self.roles_widget)
        layout.addLayout(form)

        units_label = QLabel("Jednostki organizacyjne")
        units_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(units_label)
        self.units_widget = OrganizationalUnitsWidget(
            assigned_units,
            default_unit_id,
            self,
        )
        layout.addWidget(self.units_widget, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        polish_dialog_buttons(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        QTimer.singleShot(0, self.units_widget.load_units)

    def accept(self):
        if not self.login_edit.text().strip():
            QMessageBox.warning(self, APP_NAME, "Login jest wymagany.")
            return
        if not self.name_edit.text().strip():
            QMessageBox.warning(
                self,
                APP_NAME,
                "Imię i nazwisko jest wymagane.",
            )
            return
        if not self.is_edit:
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
        if not self.roles_widget.selected_roles():
            QMessageBox.warning(
                self,
                APP_NAME,
                "Wybierz co najmniej jedną rolę.",
            )
            return
        if not self.units_widget.selected_units():
            QMessageBox.warning(
                self,
                APP_NAME,
                "Wybierz co najmniej jedną jednostkę organizacyjną.",
            )
            return
        super().accept()

    def values(self):
        values = {
            "login": self.login_edit.text().strip(),
            "full_name": self.name_edit.text().strip(),
            "role_codes": self.roles_widget.selected_roles(),
            "units": self.units_widget.selected_units(),
            "default_unit_id": self.units_widget.default_unit_id(),
        }
        if not self.is_edit:
            values["password"] = self.password_edit.text()
        return values
