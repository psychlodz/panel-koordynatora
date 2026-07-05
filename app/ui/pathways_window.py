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
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.repositories.pathway_repository import (
    add_element_at_position,
    can_delete_element,
    can_insert_before,
    create_pathway,
    delete_element_safe,
    get_element_link_counts,
    get_pathway,
    list_blocks,
    list_pathway_elements,
    list_pathways,
    reorder_elements,
    update_pathway,
    update_pathway_element,
)
from app.repositories.program_repository import get_program
from app.ui.widgets.pathway_tiles_widget import PathwayTilesWidget
from app.ui.ui_helpers import (
    ask_confirmation,
    create_help_button,
    polish_dialog_buttons,
)


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
        polish_dialog_buttons(buttons)
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
    def __init__(
        self,
        element=None,
        default_lp=1,
        pathway_elements=None,
        parent=None,
    ):
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
        self.required_checkbox.setChecked(True)
        self.order_checkbox.setChecked(True)
        self.deadline_spin = QSpinBox()
        self.deadline_spin.setRange(-1, 9999)
        self.deadline_spin.setSpecialValueText("Brak")
        self.deadline_spin.setValue(-1)
        self.deadline_unit_combo = QComboBox()
        self.deadline_unit_combo.addItem("", None)
        self.deadline_unit_combo.addItem("dzień", "DZIEN")
        self.deadline_unit_combo.addItem("tydzień", "TYDZIEN")
        self.deadline_unit_combo.addItem("miesiąc", "MIESIAC")
        self.deadline_from_combo = QComboBox()
        self.deadline_from_combo.addItem("", None)
        self.deadline_from_combo.addItem(
            "Początek programu",
            "START_PROGRAMU",
        )
        for pathway_element in pathway_elements or []:
            if (
                element is not None
                and pathway_element["element_id"] == element["element_id"]
            ):
                continue
            self.deadline_from_combo.addItem(
                f"{pathway_element['lp']}. "
                f"{pathway_element['nazwa_w_sciezce']}",
                str(pathway_element["element_id"]),
            )
        self.activation_label = QLabel()
        self.activation_label.setWordWrap(True)
        self.organization_edit = QTextEdit()

        blocks = list_blocks()
        if not blocks:
            raise ValueError("Biblioteka klocków jest pusta")
        self.blocks_by_id = {
            int(block["klocek_id"]): block for block in blocks
        }
        for block in blocks:
            self.block_combo.addItem(
                f"{block['nazwa']} "
                f"({block['typ_nazwa']} • {block['grupa_nazwa']})",
                block["klocek_id"],
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
        form.addRow("Aktywacja:", self.activation_label)
        form.addRow("Opis organizacyjny:", self.organization_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        polish_dialog_buttons(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.block_combo.currentIndexChanged.connect(self.fill_default_name)
        self.block_combo.currentIndexChanged.connect(
            self.update_activation_description
        )

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
            unit_index = self.deadline_unit_combo.findData(
                element["termin_jednostka"]
            )
            self.deadline_unit_combo.setCurrentIndex(max(0, unit_index))
            deadline_from = element["termin_od"]
            from_index = self.deadline_from_combo.findData(deadline_from)
            if deadline_from and from_index < 0:
                self.deadline_from_combo.addItem(
                    f"Dotychczasowe ustawienie: {deadline_from}",
                    deadline_from,
                )
                from_index = self.deadline_from_combo.count() - 1
            self.deadline_from_combo.setCurrentIndex(max(0, from_index))
            self.organization_edit.setPlainText(
                element["opis_organizacyjny"] or ""
            )
        else:
            self.fill_default_name()
        self.update_activation_description()

    def fill_default_name(self, _index=None):
        if self.name_edit.text().strip():
            return
        block = self.blocks_by_id.get(self.block_combo.currentData(), {})
        if block.get("nazwa"):
            self.name_edit.setText(block["nazwa"])

    def activation_value(self):
        block = self.blocks_by_id.get(self.block_combo.currentData(), {})
        block_identity = " ".join(
            str(block.get(field) or "").upper()
            for field in ("kod", "typ", "nazwa")
        )
        oracle_activated = any(
            marker in block_identity
            for marker in (
                "KONSULTAC",
                "BADANIE",
                "LAB",
                "GENET",
                "OBRAZ",
            )
        )
        return (
            "PO_WYSTAWIENIU_W_ESKULAPIE"
            if oracle_activated
            else "STATUS_EPIZODU"
        )

    def update_activation_description(self, _index=None):
        if self.activation_value() == "PO_WYSTAWIENIU_W_ESKULAPIE":
            text = (
                "Automatycznie po wystawieniu konsultacji lub badania "
                "w Eskulapie."
            )
        else:
            text = (
                "Planowanie i realizacja na podstawie statusu na liście "
                "epizodów."
            )
        self.activation_label.setText(text)

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
            "termin_jednostka": self.deadline_unit_combo.currentData(),
            "termin_od": self.deadline_from_combo.currentData(),
            "warunek_aktywacji": self.activation_value(),
            "opis_organizacyjny": self.organization_edit.toPlainText().strip() or None,
        }


class PathwaysWindow(QWidget):
    def __init__(self, program_id):
        super().__init__()
        self.program_id = program_id
        self._elements_by_id = {}
        self.dependencies_window = None
        self.triggers_window = None
        self.setWindowTitle("KOMPAS — Ścieżki")
        self.resize(1300, 720)

        layout = QVBoxLayout(self)
        self.program_label = QLabel()
        self.program_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self.program_label)

        self.refresh_button = QPushButton("Odśwież")
        self.help_button = create_help_button(
            self,
            "Ścieżki programu",
            "To okno służy do budowania ścieżek wybranego programu.\n\n"
            "Możesz przeciągać kafelki oraz dodawać i edytować elementy.\n\n"
            "Nie usuwaj elementów używanych przez aktywne epizody bez "
            "wcześniejszego sprawdzenia skutków.",
        )
        self.refresh_button.setToolTip(
            "Pobierz ponownie ścieżki i elementy programu."
        )
        self.close_button = QPushButton("Zamknij")
        self.close_button.setToolTip("Zamknij okno ścieżek programu.")
        top_actions = QHBoxLayout()
        top_actions.addWidget(self.refresh_button)
        top_actions.addWidget(self.help_button)
        top_actions.addStretch(1)
        top_actions.addWidget(self.close_button)
        layout.addLayout(top_actions)

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
        self.new_pathway_button.setToolTip("Dodaj nową ścieżkę programu.")
        self.edit_pathway_button.setToolTip("Edytuj zaznaczoną ścieżkę.")
        pathway_buttons.addWidget(self.new_pathway_button)
        pathway_buttons.addWidget(self.edit_pathway_button)
        pathways_layout.addLayout(pathway_buttons)
        splitter.addWidget(pathways_panel)

        elements_panel = QWidget()
        elements_layout = QVBoxLayout(elements_panel)
        self.elements_label = QLabel("Elementy ścieżki")
        elements_layout.addWidget(self.elements_label)

        self.elements_tabs = QTabWidget()
        self.tiles_widget = PathwayTilesWidget()
        self.elements_tabs.addTab(self.tiles_widget, "Kafelki")

        self.elements_table = QTableWidget(0, 8)
        self.elements_table.setHorizontalHeaderLabels(
            [
                "Lp.",
                "Klocek",
                "Nazwa w ścieżce",
                "Min.",
                "Maks.",
                "Obowiązkowy",
                "Wymaga zlecenia",
                "Termin",
            ]
        )
        self._configure_table(self.elements_table)
        self.elements_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.elements_tabs.addTab(self.elements_table, "Tabela")
        elements_layout.addWidget(self.elements_tabs, 1)
        element_buttons = QHBoxLayout()
        self.add_element_button = QPushButton("Dodaj element")
        self.edit_element_button = QPushButton("Edytuj element")
        self.delete_element_button = QPushButton("Usuń element")
        self.add_element_button.setToolTip(
            "Dodaj element na końcu albo przed zaznaczonym kafelkiem."
        )
        self.edit_element_button.setToolTip(
            "Edytuj zaznaczony element ścieżki."
        )
        self.delete_element_button.setToolTip(
            "Usuń zaznaczony element ze ścieżki."
        )
        element_buttons.addWidget(self.add_element_button)
        element_buttons.addWidget(self.edit_element_button)
        element_buttons.addWidget(self.delete_element_button)
        elements_layout.addLayout(element_buttons)
        splitter.addWidget(elements_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        self.refresh_button.clicked.connect(lambda: self.refresh_pathways())
        self.close_button.clicked.connect(self.close)
        self.new_pathway_button.clicked.connect(self.new_pathway)
        self.edit_pathway_button.clicked.connect(self.edit_pathway)
        self.add_element_button.clicked.connect(self.add_element)
        self.edit_element_button.clicked.connect(self.edit_element)
        self.delete_element_button.clicked.connect(self.delete_element)
        self.pathways_table.itemSelectionChanged.connect(
            self.load_selected_pathway_elements
        )
        self.elements_table.itemSelectionChanged.connect(
            self._sync_tiles_from_table
        )
        self.tiles_widget.elementSelected.connect(
            self._sync_table_from_tiles
        )
        self.tiles_widget.elementDoubleClicked.connect(
            self._edit_tile_element
        )
        self.tiles_widget.orderChanged.connect(self._tiles_reordered)

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
        if self.elements_tabs.currentWidget() is self.tiles_widget:
            return self.tiles_widget.selected_element_id()
        row = self.elements_table.currentRow()
        item = self.elements_table.item(row, 0) if row >= 0 else None
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _sync_table_from_tiles(self, element_id):
        self.elements_table.blockSignals(True)
        try:
            self.elements_table.clearSelection()
            if element_id is None:
                self.elements_table.setCurrentCell(-1, -1)
                return
            for row in range(self.elements_table.rowCount()):
                item = self.elements_table.item(row, 0)
                if (
                    item is not None
                    and int(item.data(Qt.ItemDataRole.UserRole))
                    == int(element_id)
                ):
                    self.elements_table.selectRow(row)
                    break
        finally:
            self.elements_table.blockSignals(False)

    def _sync_tiles_from_table(self):
        row = self.elements_table.currentRow()
        item = self.elements_table.item(row, 0) if row >= 0 else None
        element_id = (
            item.data(Qt.ItemDataRole.UserRole)
            if item is not None
            else None
        )
        self.tiles_widget.blockSignals(True)
        try:
            self.tiles_widget.select_element(element_id)
        finally:
            self.tiles_widget.blockSignals(False)

    def _edit_tile_element(self, element_id):
        self.tiles_widget.select_element(element_id)
        self._sync_table_from_tiles(element_id)
        self.edit_element()

    def _tiles_reordered(self, ordered_element_ids):
        pathway_id = self.current_pathway_id()
        if pathway_id is None:
            return
        selected_element_id = self.tiles_widget.selected_element_id()
        try:
            reorder_elements(pathway_id, ordered_element_ids)
            self.load_selected_pathway_elements(selected_element_id)
        except Exception as exc:
            self._show_error("Nie udało się zmienić kolejności elementów", exc)
            self.load_selected_pathway_elements(selected_element_id)

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

    def load_selected_pathway_elements(self, selected_element_id=None):
        pathway_id = self.current_pathway_id()
        if pathway_id is None:
            self.elements_table.setRowCount(0)
            self.tiles_widget.set_elements([])
            self._elements_by_id = {}
            self.elements_label.setText("Elementy ścieżki")
            return
        try:
            if selected_element_id is None:
                selected_element_id = self.current_element_id()
            pathway = get_pathway(pathway_id)
            elements = list_pathway_elements(pathway_id)
            self._elements_by_id = {
                element["element_id"]: element for element in elements
            }
            self.elements_label.setText(
                f"Elementy ścieżki: {pathway['nazwa']}"
            )
            self.tiles_widget.set_elements(
                elements,
                selected_element_id,
            )
            self.elements_table.blockSignals(True)
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
                if element["element_id"] == selected_element_id:
                    self.elements_table.selectRow(row_index)
            self.elements_table.blockSignals(False)
        except Exception as exc:
            self.elements_table.blockSignals(False)
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

        position, accepted = QInputDialog.getItem(
            self,
            "KOMPAS — Miejsce elementu",
            "Gdzie wstawić nowy element?",
            ["Na końcu", "Przed zaznaczonym elementem"],
            0,
            False,
        )
        if not accepted:
            return

        before_element_id = None
        if position == "Przed zaznaczonym elementem":
            before_element_id = self.current_element_id()
            if before_element_id is None:
                QMessageBox.information(
                    self,
                    "KOMPAS",
                    "Zaznacz element, przed którym ma zostać wstawiony "
                    "nowy kafelek.",
                )
                return
            try:
                insert_allowed = can_insert_before(before_element_id)
            except Exception as exc:
                self._show_error(
                    "Nie udało się sprawdzić możliwości wstawienia elementu",
                    exc,
                )
                return
            if not insert_allowed:
                QMessageBox.warning(
                    self,
                    "KOMPAS — Operacja zablokowana",
                    "Nie można dodać nowego elementu przed zaznaczonym "
                    "elementem, ponieważ ma on zadanie o statusie "
                    "ZREALIZOWANO.",
                )
                return

        default_lp = (
            self._elements_by_id[before_element_id]["lp"]
            if before_element_id is not None
            else max(
                [
                    element["lp"]
                    for element in self._elements_by_id.values()
                ],
                default=0,
            )
            + 1
        )
        try:
            dialog = PathwayElementDialog(
                default_lp=default_lp,
                pathway_elements=list(self._elements_by_id.values()),
                parent=self,
            )
            dialog.position_spin.setEnabled(False)
            dialog.position_spin.setToolTip(
                "Pozycja zostanie wyliczona automatycznie."
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            values = dialog.values()
            values.pop("lp", None)
            element_id = add_element_at_position(
                pathway_id,
                before_element_id=before_element_id,
                **values,
            )
            self.load_selected_pathway_elements(element_id)
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
            dialog = PathwayElementDialog(
                element,
                pathway_elements=list(self._elements_by_id.values()),
                parent=self,
            )
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

        try:
            delete_allowed = can_delete_element(element_id)
            links = (
                get_element_link_counts(element_id)
                if delete_allowed
                else {"dependencies": 0, "triggers": 0}
            )
        except Exception as exc:
            self._show_error(
                "Nie udało się sprawdzić możliwości usunięcia elementu",
                exc,
            )
            return

        if not delete_allowed:
            QMessageBox.warning(
                self,
                "KOMPAS — Operacja zablokowana",
                "Nie można usunąć elementu, ponieważ istnieje powiązane "
                "zadanie o statusie ZREALIZOWANO.",
            )
            return

        warning = ""
        if links["dependencies"] or links["triggers"]:
            warning = (
                "\n\nElement jest używany przez "
                f"{links['dependencies']} zależności i "
                f"{links['triggers']} wyzwalacze. "
                "Kontynuowanie usunie również te powiązania."
            )
        if not ask_confirmation(
            self,
            "Czy na pewno usunąć wybrany element ścieżki?"
            + warning,
        ):
            return
        try:
            delete_element_safe(element_id)
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

    def open_pathway_units(self):
        pathway_id = self.current_pathway_id()
        if pathway_id is None:
            QMessageBox.information(
                self,
                "KOMPAS",
                "Wybierz ścieżkę, aby przypisać jednostki.",
            )
            return
        try:
            from app.ui.unit_assignments_dialog import UnitAssignmentsDialog

            dialog = UnitAssignmentsDialog("pathway", pathway_id, self)
            dialog.exec()
        except Exception as exc:
            self._show_error("Nie udało się otworzyć jednostek ścieżki", exc)

    def open_triggers(self):
        element_id = self.current_element_id()
        if element_id is None:
            QMessageBox.information(
                self, "KOMPAS", "Wybierz element, aby otworzyć wyzwalacze."
            )
            return
        element = self._elements_by_id.get(element_id)
        if element is None:
            self.load_selected_pathway_elements()
            return
        try:
            from app.ui.triggers_window import TriggersWindow

            self.triggers_window = TriggersWindow(element)
            self.triggers_window.show()
        except Exception as exc:
            self._show_error("Nie udało się otworzyć wyzwalaczy", exc)
