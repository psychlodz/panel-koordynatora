from PySide6.QtCore import Qt
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
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.repositories.pathway_repository import (
    add_element_to_pathway,
    create_pathway,
    delete_pathway_element,
    get_pathway,
    list_blocks,
    list_pathway_elements,
    list_pathways,
    update_pathway,
    update_pathway_element,
)
from app.repositories.program_repository import get_program


class PathwayDialog(QDialog):
    def __init__(self, pathway=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(
            "KOMPAS — Edytuj ścieżkę"
            if pathway
            else "KOMPAS — Nowa ścieżka"
        )
        self.resize(520, 340)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.description_edit = QTextEdit()
        self.active_checkbox = QCheckBox("Ścieżka aktywna")
        self.active_checkbox.setChecked(True)
        form.addRow("Kod:", self.code_edit)
        form.addRow("Nazwa:", self.name_edit)
        form.addRow("Opis:", self.description_edit)
        if pathway is not None:
            form.addRow("Status:", self.active_checkbox)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if pathway is not None:
            self.code_edit.setText(pathway["kod"] or "")
            self.name_edit.setText(pathway["nazwa"] or "")
            self.description_edit.setPlainText(pathway["opis"] or "")
            self.active_checkbox.setChecked(bool(pathway["czy_aktywna"]))

    def accept(self):
        if not self.code_edit.text().strip():
            QMessageBox.warning(self, "KOMPAS", "Kod ścieżki jest wymagany.")
            return
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "KOMPAS", "Nazwa ścieżki jest wymagana.")
            return
        super().accept()

    def values(self) -> dict:
        return {
            "kod": self.code_edit.text().strip(),
            "nazwa": self.name_edit.text().strip(),
            "opis": self.description_edit.toPlainText().strip() or None,
            "czy_aktywna": 1 if self.active_checkbox.isChecked() else 0,
        }


class PathwayElementDialog(QDialog):
    def __init__(self, element=None, default_lp=1, parent=None):
        super().__init__(parent)
        self.setWindowTitle(
            "KOMPAS — Edytuj element"
            if element
            else "KOMPAS — Dodaj element"
        )
        self.resize(680, 720)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.block_combo = QComboBox()
        self.name_edit = QLineEdit()
        self.position_spin = QSpinBox()
        self.position_spin.setRange(1, 9999)
        self.position_spin.setValue(default_lp)
        self.min_spin = QSpinBox()
        self.min_spin.setRange(0, 9999)
        self.max_spin = QSpinBox()
        self.max_spin.setRange(-1, 9999)
        self.max_spin.setSpecialValueText("Brak")
        self.max_spin.setValue(-1)
        self.required_checkbox = QCheckBox("Element obowiązkowy")
        self.order_checkbox = QCheckBox("Wymaga zlecenia lekarza")
        self.deadline_spin = QSpinBox()
        self.deadline_spin.setRange(-1, 9999)
        self.deadline_spin.setSpecialValueText("Brak")
        self.deadline_spin.setValue(-1)
        self.deadline_unit_combo = QComboBox()
        self.deadline_unit_combo.setEditable(True)
        self.deadline_unit_combo.addItems(["", "DZIEN", "TYDZIEN", "MIESIAC"])
        self.deadline_from_combo = QComboBox()
        self.deadline_from_combo.setEditable(True)
        self.deadline_from_combo.addItems(
            ["", "START_PROGRAMU", "POPRZEDNI_ELEMENT", "DATA_ZLECENIA"]
        )
        self.activation_edit = QLineEdit()
        self.organization_edit = QTextEdit()

        blocks = list_blocks()
        if not blocks:
            raise ValueError("Biblioteka klocków jest pusta")
        for block in blocks:
            self.block_combo.addItem(
                f"{block['kod']} — {block['nazwa']}", block["klocek_id"]
            )

        form.addRow("Klocek:", self.block_combo)
        form.addRow("Nazwa w ścieżce:", self.name_edit)
        form.addRow("Lp:", self.position_spin)
        form.addRow("Minimalna liczba:", self.min_spin)
        form.addRow("Maksymalna liczba:", self.max_spin)
        form.addRow("Obowiązkowość:", self.required_checkbox)
        form.addRow("Zlecenie:", self.order_checkbox)
        form.addRow("Termin — liczba:", self.deadline_spin)
        form.addRow("Termin — jednostka:", self.deadline_unit_combo)
        form.addRow("Termin liczony od:", self.deadline_from_combo)
        form.addRow("Warunek aktywacji:", self.activation_edit)
        form.addRow("Opis organizacyjny:", self.organization_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.block_combo.currentIndexChanged.connect(self.fill_default_name)

        if element is not None:
            index = self.block_combo.findData(element["klocek_id"])
            if index >= 0:
                self.block_combo.setCurrentIndex(index)
            self.name_edit.setText(element["nazwa_w_sciezce"] or "")
            self.position_spin.setValue(element["lp"])
            self.min_spin.setValue(element["min_liczba"] or 0)
            self.max_spin.setValue(
                -1 if element["max_liczba"] is None else element["max_liczba"]
            )
            self.required_checkbox.setChecked(bool(element["czy_obowiazkowy"]))
            self.order_checkbox.setChecked(
                bool(element["czy_wymaga_zlecenia"])
            )
            self.deadline_spin.setValue(
                -1
                if element["termin_liczba"] is None
                else element["termin_liczba"]
            )
            self.deadline_unit_combo.setCurrentText(
                element["termin_jednostka"] or ""
            )
            self.deadline_from_combo.setCurrentText(element["termin_od"] or "")
            self.activation_edit.setText(element["warunek_aktywacji"] or "")
            self.organization_edit.setPlainText(
                element["opis_organizacyjny"] or ""
            )
        else:
            self.fill_default_name()

    def fill_default_name(self, _index=None):
        if self.name_edit.text().strip():
            return
        text = self.block_combo.currentText()
        if " — " in text:
            self.name_edit.setText(text.split(" — ", 1)[1])

    def accept(self):
        if self.block_combo.currentData() is None:
            QMessageBox.warning(self, "KOMPAS", "Wybierz klocek.")
            return
        if not self.name_edit.text().strip():
            QMessageBox.warning(
                self, "KOMPAS", "Nazwa elementu w ścieżce jest wymagana."
            )
            return
        if self.max_spin.value() >= 0 and self.max_spin.value() < self.min_spin.value():
            QMessageBox.warning(
                self,
                "KOMPAS",
                "Maksymalna liczba nie może być mniejsza od minimalnej.",
            )
            return
        super().accept()

    def values(self) -> dict:
        return {
            "klocek_id": self.block_combo.currentData(),
            "lp": self.position_spin.value(),
            "nazwa_w_sciezce": self.name_edit.text().strip(),
            "min_liczba": self.min_spin.value(),
            "max_liczba": None if self.max_spin.value() < 0 else self.max_spin.value(),
            "czy_obowiazkowy": 1 if self.required_checkbox.isChecked() else 0,
            "czy_wymaga_zlecenia": 1 if self.order_checkbox.isChecked() else 0,
            "termin_liczba": None if self.deadline_spin.value() < 0 else self.deadline_spin.value(),
            "termin_jednostka": self.deadline_unit_combo.currentText().strip() or None,
            "termin_od": self.deadline_from_combo.currentText().strip() or None,
            "warunek_aktywacji": self.activation_edit.text().strip() or None,
            "opis_organizacyjny": self.organization_edit.toPlainText().strip() or None,
        }


class PathwaysWindow(QWidget):
    def __init__(self, program_id):
        super().__init__()
        self.program_id = program_id
        self._elements_by_id = {}
        self.dependencies_window = None
        self.setWindowTitle("KOMPAS — Ścieżki")
        self.resize(1300, 720)

        layout = QVBoxLayout(self)
        self.program_label = QLabel()
        self.program_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self.program_label)

        self.refresh_button = QPushButton("Odśwież")
        layout.addWidget(self.refresh_button, alignment=Qt.AlignmentFlag.AlignLeft)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        pathways_panel = QWidget()
        pathways_layout = QVBoxLayout(pathways_panel)
        pathways_layout.addWidget(QLabel("Ścieżki programu"))
        self.pathways_table = QTableWidget(0, 4)
        self.pathways_table.setHorizontalHeaderLabels(
            ["ID", "Kod", "Nazwa", "Aktywna"]
        )
        self._configure_table(self.pathways_table)
        self.pathways_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        pathways_layout.addWidget(self.pathways_table, 1)
        pathway_buttons = QHBoxLayout()
        self.new_pathway_button = QPushButton("Nowa ścieżka")
        self.edit_pathway_button = QPushButton("Edytuj ścieżkę")
        self.dependencies_button = QPushButton("Zależności")
        pathway_buttons.addWidget(self.new_pathway_button)
        pathway_buttons.addWidget(self.edit_pathway_button)
        pathway_buttons.addWidget(self.dependencies_button)
        pathways_layout.addLayout(pathway_buttons)
        splitter.addWidget(pathways_panel)

        elements_panel = QWidget()
        elements_layout = QVBoxLayout(elements_panel)
        self.elements_label = QLabel("Elementy ścieżki")
        elements_layout.addWidget(self.elements_label)
        self.elements_table = QTableWidget(0, 8)
        self.elements_table.setHorizontalHeaderLabels(
            ["Lp", "Klocek", "Nazwa w ścieżce", "Min", "Max", "Obow.", "Zlecenie", "Termin"]
        )
        self._configure_table(self.elements_table)
        self.elements_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        elements_layout.addWidget(self.elements_table, 1)
        element_buttons = QHBoxLayout()
        self.add_element_button = QPushButton("Dodaj element")
        self.edit_element_button = QPushButton("Edytuj element")
        self.delete_element_button = QPushButton("Usuń element")
        element_buttons.addWidget(self.add_element_button)
        element_buttons.addWidget(self.edit_element_button)
        element_buttons.addWidget(self.delete_element_button)
        elements_layout.addLayout(element_buttons)
        splitter.addWidget(elements_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        self.refresh_button.clicked.connect(lambda: self.refresh_pathways())
        self.new_pathway_button.clicked.connect(self.new_pathway)
        self.edit_pathway_button.clicked.connect(self.edit_pathway)
        self.dependencies_button.clicked.connect(self.open_dependencies)
        self.add_element_button.clicked.connect(self.add_element)
        self.edit_element_button.clicked.connect(self.edit_element)
        self.delete_element_button.clicked.connect(self.delete_element)
        self.pathways_table.itemSelectionChanged.connect(
            self.load_selected_pathway_elements
        )

        self.refresh_pathways()

    def _configure_table(self, table):
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )

    def _show_error(self, message, exc):
        QMessageBox.critical(self, "KOMPAS", f"{message}: {exc}")

    def current_pathway_id(self):
        row = self.pathways_table.currentRow()
        item = self.pathways_table.item(row, 0) if row >= 0 else None
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def current_element_id(self):
        row = self.elements_table.currentRow()
        item = self.elements_table.item(row, 0) if row >= 0 else None
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def refresh_pathways(self, select_id=None):
        try:
            program = get_program(self.program_id)
            if program is None:
                raise ValueError("Wybrany program nie istnieje")
            self.program_label.setText(
                f"Program: {program['kod']} — {program['nazwa']}"
            )
            if select_id is None:
                select_id = self.current_pathway_id()
            pathways = list_pathways(self.program_id)
            self.pathways_table.blockSignals(True)
            self.pathways_table.setRowCount(len(pathways))
            selected_row = 0 if pathways else -1
            for row_index, pathway in enumerate(pathways):
                values = [
                    str(pathway["sciezka_id"]),
                    pathway["kod"],
                    pathway["nazwa"],
                    "Tak" if pathway["czy_aktywna"] else "Nie",
                ]
                for column_index, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    if column_index == 0:
                        item.setData(
                            Qt.ItemDataRole.UserRole, pathway["sciezka_id"]
                        )
                    self.pathways_table.setItem(row_index, column_index, item)
                if pathway["sciezka_id"] == select_id:
                    selected_row = row_index
            if selected_row >= 0:
                self.pathways_table.selectRow(selected_row)
            self.pathways_table.blockSignals(False)
            self.load_selected_pathway_elements()
        except Exception as exc:
            self._show_error("Nie udało się pobrać ścieżek", exc)

    def load_selected_pathway_elements(self):
        pathway_id = self.current_pathway_id()
        if pathway_id is None:
            self.elements_table.setRowCount(0)
            self._elements_by_id = {}
            self.elements_label.setText("Elementy ścieżki")
            return
        try:
            pathway = get_pathway(pathway_id)
            elements = list_pathway_elements(pathway_id)
            self._elements_by_id = {
                element["element_id"]: element for element in elements
            }
            self.elements_label.setText(
                f"Elementy ścieżki: {pathway['nazwa']}"
            )
            self.elements_table.setRowCount(len(elements))
            for row_index, element in enumerate(elements):
                if element["termin_liczba"] is None:
                    deadline = ""
                else:
                    deadline = str(element["termin_liczba"])
                    if element["termin_jednostka"]:
                        deadline += f" {element['termin_jednostka']}"
                    if element["termin_od"]:
                        deadline += f" od {element['termin_od']}"
                values = [
                    str(element["lp"]),
                    element["klocek_kod"],
                    element["nazwa_w_sciezce"],
                    str(element["min_liczba"]),
                    "" if element["max_liczba"] is None else str(element["max_liczba"]),
                    "Tak" if element["czy_obowiazkowy"] else "Nie",
                    "Tak" if element["czy_wymaga_zlecenia"] else "Nie",
                    deadline,
                ]
                for column_index, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    if column_index == 0:
                        item.setData(
                            Qt.ItemDataRole.UserRole, element["element_id"]
                        )
                    self.elements_table.setItem(row_index, column_index, item)
        except Exception as exc:
            self._show_error("Nie udało się pobrać elementów", exc)

    def new_pathway(self):
        dialog = PathwayDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        try:
            pathway_id = create_pathway(
                self.program_id,
                values["kod"],
                values["nazwa"],
                values["opis"],
            )
            self.refresh_pathways(pathway_id)
        except Exception as exc:
            self._show_error("Nie udało się utworzyć ścieżki", exc)

    def edit_pathway(self):
        pathway_id = self.current_pathway_id()
        if pathway_id is None:
            QMessageBox.information(self, "KOMPAS", "Wybierz ścieżkę do edycji.")
            return
        try:
            pathway = get_pathway(pathway_id)
            if pathway is None:
                raise ValueError("Wybrana ścieżka nie istnieje")
            dialog = PathwayDialog(pathway, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            values = dialog.values()
            update_pathway(
                pathway_id,
                values["kod"],
                values["nazwa"],
                values["opis"],
                values["czy_aktywna"],
            )
            self.refresh_pathways(pathway_id)
        except Exception as exc:
            self._show_error("Nie udało się zaktualizować ścieżki", exc)

    def add_element(self):
        pathway_id = self.current_pathway_id()
        if pathway_id is None:
            QMessageBox.information(self, "KOMPAS", "Wybierz ścieżkę.")
            return
        default_lp = max(
            [element["lp"] for element in self._elements_by_id.values()],
            default=0,
        ) + 1
        try:
            dialog = PathwayElementDialog(default_lp=default_lp, parent=self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            add_element_to_pathway(pathway_id, **dialog.values())
            self.load_selected_pathway_elements()
        except Exception as exc:
            self._show_error("Nie udało się dodać elementu", exc)

    def edit_element(self):
        element_id = self.current_element_id()
        if element_id is None:
            QMessageBox.information(self, "KOMPAS", "Wybierz element do edycji.")
            return
        element = self._elements_by_id.get(element_id)
        if element is None:
            self.load_selected_pathway_elements()
            return
        try:
            dialog = PathwayElementDialog(element, parent=self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            update_pathway_element(element_id, **dialog.values())
            self.load_selected_pathway_elements()
        except Exception as exc:
            self._show_error("Nie udało się zaktualizować elementu", exc)

    def delete_element(self):
        element_id = self.current_element_id()
        if element_id is None:
            QMessageBox.information(self, "KOMPAS", "Wybierz element do usunięcia.")
            return
        answer = QMessageBox.question(
            self,
            "KOMPAS",
            "Czy na pewno usunąć wybrany element ścieżki?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            delete_pathway_element(element_id)
            self.load_selected_pathway_elements()
        except Exception as exc:
            self._show_error("Nie udało się usunąć elementu", exc)

    def open_dependencies(self):
        pathway_id = self.current_pathway_id()
        if pathway_id is None:
            QMessageBox.information(
                self, "KOMPAS", "Wybierz ścieżkę, aby otworzyć zależności."
            )
            return
        try:
            from app.ui.dependencies_window import DependenciesWindow

            self.dependencies_window = DependenciesWindow(pathway_id)
            self.dependencies_window.show()
        except Exception as exc:
            self._show_error("Nie udało się otworzyć zależności", exc)
