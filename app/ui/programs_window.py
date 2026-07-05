from PySide6.QtCore import QTimer, Qt
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.gateway.eskulap_gateway import EskulapGateway
from app.repositories.program_repository import (
    create_program,
    get_program,
    list_programs,
    update_program,
)
from app.repositories.program_unit_repository import list_program_units
from app.ui.ui_helpers import create_help_button, polish_dialog_buttons
from app.ui.widgets.busy_indicator import busy_operation


def _unit_dict(unit):
    if isinstance(unit, dict):
        getter = unit.get
    else:
        getter = lambda name: getattr(unit, name, None)
    return {
        "jo_id": str(getter("jo_id") or "").strip(),
        "jo_symbol": getter("jo_symbol"),
        "jo_nazwa": getter("jo_nazwa"),
    }


class ProgramUnitsChecklist(QWidget):
    def __init__(self, selected_units=None, parent=None):
        super().__init__(parent)
        self.units = {}
        normalized_selected = [
            _unit_dict(unit)
            for unit in (selected_units or [])
        ]
        self.selected_ids = {
            unit["jo_id"]
            for unit in normalized_selected
            if unit["jo_id"]
        }

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        tools = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(
            "Filtruj jednostki organizacyjne..."
        )
        self.refresh_button = QPushButton("Pobierz z Eskulapa")
        tools.addWidget(self.search_edit, 1)
        tools.addWidget(self.refresh_button)
        layout.addLayout(tools)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(
            ["Symbol", "Nazwa", "Identyfikator"]
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

        for normalized in normalized_selected:
            if normalized["jo_id"]:
                self.units[normalized["jo_id"]] = normalized
        self._populate()

        self.refresh_button.clicked.connect(self.load_units)
        self.search_edit.textChanged.connect(self.apply_filter)
        self.table.itemChanged.connect(self._item_changed)

    def load_units(self):
        try:
            with busy_operation(
                self.window(),
                "Trwa pobieranie jednostek organizacyjnych z Eskulapa...",
            ):
                units = EskulapGateway().list_organizational_units()
            for unit in units:
                normalized = _unit_dict(unit)
                if normalized["jo_id"]:
                    self.units[normalized["jo_id"]] = normalized
            self._populate()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się pobrać jednostek z Eskulapa:\n\n{exc}",
            )

    def _populate(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.units))
        for row, unit in enumerate(self.units.values()):
            symbol_item = QTableWidgetItem(
                str(unit["jo_symbol"] or "")
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
                if unit["jo_id"] in self.selected_ids
                else Qt.CheckState.Unchecked
            )
            self.table.setItem(row, 0, symbol_item)
            self.table.setItem(
                row,
                1,
                QTableWidgetItem(str(unit["jo_nazwa"] or "")),
            )
            self.table.setItem(
                row,
                2,
                QTableWidgetItem(unit["jo_id"]),
            )
        self.table.blockSignals(False)
        self.apply_filter(self.search_edit.text())

    def _item_changed(self, item):
        if item.column() != 0:
            return
        unit_id = str(item.data(Qt.ItemDataRole.UserRole))
        if item.checkState() == Qt.CheckState.Checked:
            self.selected_ids.add(unit_id)
        else:
            self.selected_ids.discard(unit_id)

    def apply_filter(self, text):
        pattern = str(text or "").strip().casefold()
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
            unit
            for unit_id, unit in self.units.items()
            if unit_id in self.selected_ids
        ]


class ProgramDialog(QDialog):
    def __init__(self, program=None, selected_units=None, parent=None):
        super().__init__(parent)
        self._program = program
        self.setWindowTitle(
            "KOMPAS — Edytuj program"
            if program
            else "KOMPAS — Nowy program"
        )
        self.resize(760, 700)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.version_edit = QLineEdit()
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        self.active_checkbox = QCheckBox("Program aktywny")
        self.active_checkbox.setChecked(True)

        form.addRow("Kod:", self.code_edit)
        form.addRow("Nazwa:", self.name_edit)
        form.addRow("Wersja:", self.version_edit)
        form.addRow("Opis:", self.description_edit)
        if program is not None:
            form.addRow("Status:", self.active_checkbox)
        layout.addLayout(form)

        units_label = QLabel("Jednostki organizacyjne")
        units_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(units_label)
        self.units_widget = ProgramUnitsChecklist(
            selected_units,
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

        if program is not None:
            self.code_edit.setText(program["kod"] or "")
            self.name_edit.setText(program["nazwa"] or "")
            self.version_edit.setText(program["wersja"] or "")
            self.description_edit.setPlainText(program["opis"] or "")
            self.active_checkbox.setChecked(bool(program["czy_aktywny"]))

        QTimer.singleShot(0, self.units_widget.load_units)

    def accept(self):
        if not self.code_edit.text().strip():
            QMessageBox.warning(
                self,
                "KOMPAS",
                "Kod programu jest wymagany.",
            )
            return
        if not self.name_edit.text().strip():
            QMessageBox.warning(
                self,
                "KOMPAS",
                "Nazwa programu jest wymagana.",
            )
            return
        super().accept()

    def values(self):
        return {
            "kod": self.code_edit.text().strip(),
            "nazwa": self.name_edit.text().strip(),
            "wersja": self.version_edit.text().strip() or None,
            "opis": self.description_edit.toPlainText().strip() or None,
            "czy_aktywny": 1 if self.active_checkbox.isChecked() else 0,
            "units": self.units_widget.selected_units(),
        }


class ProgramsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KOMPAS - Programy")
        self.resize(1000, 560)
        self.pathways_window = None

        layout = QVBoxLayout(self)
        title = QLabel("KOMPAS - Programy")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Kod", "Nazwa", "Wersja", "Jednostki", "Aktywny"]
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
            2,
            QHeaderView.ResizeMode.Stretch,
        )
        layout.addWidget(self.table, 1)

        buttons = QHBoxLayout()
        self.refresh_button = QPushButton("Odśwież")
        self.new_button = QPushButton("Nowy")
        self.edit_button = QPushButton("Edytuj")
        self.paths_button = QPushButton("Ścieżki")
        self.help_button = create_help_button(
            self,
            "Programy",
            "To okno służy do zarządzania programami KOMPAS oraz ich "
            "dostępnością w jednostkach organizacyjnych.",
        )
        self.close_button = QPushButton("Zamknij")
        self.refresh_button.setToolTip("Pobierz ponownie listę programów.")
        self.new_button.setToolTip(
            "Dodaj program i wybierz jego jednostki organizacyjne."
        )
        self.edit_button.setToolTip(
            "Edytuj program i przypisane jednostki."
        )
        self.paths_button.setToolTip(
            "Otwórz ścieżki należące do zaznaczonego programu."
        )
        self.close_button.setToolTip("Zamknij okno programów.")
        for button in (
            self.refresh_button,
            self.new_button,
            self.edit_button,
            self.paths_button,
            self.help_button,
        ):
            buttons.addWidget(button)
        buttons.addStretch(1)
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)

        self.refresh_button.clicked.connect(self.refresh_programs)
        self.new_button.clicked.connect(self.new_program)
        self.edit_button.clicked.connect(self.edit_program)
        self.paths_button.clicked.connect(self.open_pathways)
        self.close_button.clicked.connect(self.close)
        self.refresh_programs()

    def refresh_programs(self):
        try:
            with busy_operation(
                self,
                "Trwa pobieranie listy programów...",
            ):
                programs = list_programs()
            self.table.setRowCount(len(programs))
            for row_index, program in enumerate(programs):
                values = [
                    str(program["program_id"]),
                    program["kod"] or "",
                    program["nazwa"] or "",
                    program["wersja"] or "",
                    program.get("jednostki") or "",
                    "Tak" if program["czy_aktywny"] else "Nie",
                ]
                for column_index, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    if column_index == 0:
                        item.setData(
                            Qt.ItemDataRole.UserRole,
                            program["program_id"],
                        )
                    self.table.setItem(row_index, column_index, item)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się pobrać listy programów:\n\n{exc}",
            )

    def selected_program_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def new_program(self):
        dialog = ProgramDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            values = dialog.values()
            create_program(
                values["kod"],
                values["nazwa"],
                values["wersja"],
                values["opis"],
                values["units"],
            )
            self.refresh_programs()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się utworzyć programu:\n\n{exc}",
            )

    def edit_program(self):
        program_id = self.selected_program_id()
        if program_id is None:
            QMessageBox.information(
                self,
                "KOMPAS",
                "Wybierz program do edycji.",
            )
            return
        try:
            program = get_program(program_id)
            if program is None:
                raise ValueError("Wybrany program już nie istnieje")
            selected_units = list_program_units(program_id)
            dialog = ProgramDialog(
                program,
                selected_units,
                self,
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            values = dialog.values()
            update_program(
                program_id,
                values["kod"],
                values["nazwa"],
                values["wersja"],
                values["opis"],
                values["czy_aktywny"],
                values["units"],
            )
            self.refresh_programs()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się zaktualizować programu:\n\n{exc}",
            )

    def open_pathways(self):
        program_id = self.selected_program_id()
        if program_id is None:
            QMessageBox.information(
                self,
                "KOMPAS",
                "Wybierz program, aby otworzyć jego ścieżki.",
            )
            return
        try:
            from app.ui.pathways_window import PathwaysWindow

            self.pathways_window = PathwaysWindow(program_id)
            self.pathways_window.show()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się otworzyć ścieżek: {exc}",
            )
