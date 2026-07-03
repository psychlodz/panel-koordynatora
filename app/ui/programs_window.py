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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.repositories.program_repository import (
    create_program,
    get_program,
    list_programs,
    update_program,
)


class ProgramDialog(QDialog):
    def __init__(self, program=None, parent=None):
        super().__init__(parent)
        self._program = program
        self.setWindowTitle(
            "KOMPAS — Edytuj program" if program else "KOMPAS — Nowy program"
        )
        self.resize(520, 360)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.version_edit = QLineEdit()
        self.description_edit = QTextEdit()
        self.active_checkbox = QCheckBox("Program aktywny")
        self.active_checkbox.setChecked(True)

        form.addRow("Kod:", self.code_edit)
        form.addRow("Nazwa:", self.name_edit)
        form.addRow("Wersja:", self.version_edit)
        form.addRow("Opis:", self.description_edit)
        if program is not None:
            form.addRow("Status:", self.active_checkbox)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if program is not None:
            self.code_edit.setText(program["kod"] or "")
            self.name_edit.setText(program["nazwa"] or "")
            self.version_edit.setText(program["wersja"] or "")
            self.description_edit.setPlainText(program["opis"] or "")
            self.active_checkbox.setChecked(bool(program["czy_aktywny"]))

    def accept(self):
        if not self.code_edit.text().strip():
            QMessageBox.warning(self, "KOMPAS", "Kod programu jest wymagany.")
            return
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "KOMPAS", "Nazwa programu jest wymagana.")
            return
        super().accept()

    def values(self) -> dict:
        return {
            "kod": self.code_edit.text().strip(),
            "nazwa": self.name_edit.text().strip(),
            "wersja": self.version_edit.text().strip() or None,
            "opis": self.description_edit.toPlainText().strip() or None,
            "czy_aktywny": 1 if self.active_checkbox.isChecked() else 0,
        }


class ProgramsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KOMPAS — Programy")
        self.resize(900, 520)

        layout = QVBoxLayout(self)
        title = QLabel("Programy KOMPAS")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Kod", "Nazwa", "Wersja", "Aktywny"]
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
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        layout.addWidget(self.table, 1)

        buttons = QHBoxLayout()
        self.refresh_button = QPushButton("Odśwież")
        self.new_button = QPushButton("Nowy")
        self.edit_button = QPushButton("Edytuj")
        self.paths_button = QPushButton("Ścieżki")
        buttons.addWidget(self.refresh_button)
        buttons.addWidget(self.new_button)
        buttons.addWidget(self.edit_button)
        buttons.addWidget(self.paths_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.refresh_button.clicked.connect(self.refresh_programs)
        self.new_button.clicked.connect(self.new_program)
        self.edit_button.clicked.connect(self.edit_program)
        self.paths_button.clicked.connect(self.show_paths_placeholder)

        self.refresh_programs()

    def refresh_programs(self):
        try:
            programs = list_programs()
            self.table.setRowCount(len(programs))
            for row_index, program in enumerate(programs):
                values = [
                    str(program["program_id"]),
                    program["kod"] or "",
                    program["nazwa"] or "",
                    program["wersja"] or "",
                    "Tak" if program["czy_aktywny"] else "Nie",
                ]
                for column_index, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    if column_index == 0:
                        item.setData(
                            Qt.ItemDataRole.UserRole, program["program_id"]
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
        values = dialog.values()
        try:
            create_program(
                values["kod"],
                values["nazwa"],
                values["wersja"],
                values["opis"],
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
                self, "KOMPAS", "Wybierz program do edycji."
            )
            return

        program = get_program(program_id)
        if program is None:
            QMessageBox.warning(
                self, "KOMPAS", "Wybrany program już nie istnieje."
            )
            self.refresh_programs()
            return

        dialog = ProgramDialog(program, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        try:
            update_program(
                program_id,
                values["kod"],
                values["nazwa"],
                values["wersja"],
                values["opis"],
                values["czy_aktywny"],
            )
            self.refresh_programs()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się zaktualizować programu:\n\n{exc}",
            )

    def show_paths_placeholder(self):
        QMessageBox.information(
            self, "KOMPAS", "Moduł ścieżek w przygotowaniu."
        )
