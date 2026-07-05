from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.gateway.eskulap_gateway import EskulapGateway
from app.models.visit_parameter import VisitParameter
from app.repositories.visit_mapping_repository import (
    assign_visit_parameter,
    delete_visit_mapping,
    list_mapping_blocks,
    list_visit_mappings,
)
from app.ui.widgets.busy_indicator import busy_operation


MAPPING_ID_ROLE = int(Qt.ItemDataRole.UserRole) + 1
PARAMETER_NAME_ROLE = int(Qt.ItemDataRole.UserRole) + 2


class VisitMappingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._blocks = []
        self._parameters = []
        self._mappings_by_code = {}

        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.only_active_checkbox = QCheckBox(
            "Pokaż tylko aktywne rodzaje wizyt"
        )
        self.only_active_checkbox.setChecked(True)
        self.refresh_button = QPushButton("Odśwież")
        self.refresh_button.setToolTip(
            "Pobierz klocki z PostgreSQL i rodzaje wizyt z Eskulapa."
        )
        controls.addWidget(self.only_active_checkbox)
        controls.addStretch(1)
        controls.addWidget(self.refresh_button)
        layout.addLayout(controls)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.blocks_table = QTableWidget(0, 3)
        self.blocks_table.setHorizontalHeaderLabels(
            ["Klocek", "Grupa", "Mapowania"]
        )
        self.parameters_table = QTableWidget(0, 4)
        self.parameters_table.setHorizontalHeaderLabels(
            ["Kod WP_PARAMETR", "Nazwa w Eskulapie", "Aktywny", "Klocek"]
        )
        for table in (self.blocks_table, self.parameters_table):
            table.setSelectionBehavior(
                QAbstractItemView.SelectionBehavior.SelectRows
            )
            table.setEditTriggers(
                QAbstractItemView.EditTrigger.NoEditTriggers
            )
            table.verticalHeader().setVisible(False)
            table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents
            )
        self.blocks_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.parameters_table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.blocks_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.parameters_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        splitter.addWidget(self.blocks_table)
        splitter.addWidget(self.parameters_table)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        actions = QHBoxLayout()
        self.assign_button = QPushButton("Przypisz zaznaczone")
        self.assign_button.setToolTip(
            "Przypisz zaznaczone rodzaje wizyt do wybranego klocka."
        )
        self.remove_button = QPushButton("Usuń przypisanie")
        self.remove_button.setToolTip(
            "Usuń przypisania zaznaczonych rodzajów wizyt."
        )
        actions.addWidget(self.assign_button)
        actions.addWidget(self.remove_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.refresh_button.clicked.connect(self.refresh)
        self.only_active_checkbox.toggled.connect(self.refresh)
        self.assign_button.clicked.connect(self.assign_selected)
        self.remove_button.clicked.connect(self.remove_selected)
        QTimer.singleShot(0, self.refresh)

    def selected_block_id(self):
        row = self.blocks_table.currentRow()
        item = self.blocks_table.item(row, 0) if row >= 0 else None
        return (
            item.data(Qt.ItemDataRole.UserRole)
            if item is not None
            else None
        )

    def selected_parameter_rows(self):
        return sorted(
            {index.row() for index in self.parameters_table.selectedIndexes()}
        )

    @staticmethod
    def _active_text(value):
        return (
            "Tak"
            if str(value if value is not None else "T").strip().upper()
            in {"T", "TAK", "Y", "YES", "1", "TRUE"}
            else "Nie"
        )

    def refresh(self):
        selected_block = self.selected_block_id()
        try:
            with busy_operation(
                self,
                "Trwa pobieranie rodzajów wizyt i mapowań...",
            ):
                self._blocks = list_mapping_blocks(only_active=True)
                mappings = list_visit_mappings(only_active=True)
                self._parameters = EskulapGateway().list_visit_parameters(
                    only_active=self.only_active_checkbox.isChecked(),
                )
            self._mappings_by_code = {
                str(item["parametr_kod"]).upper(): item
                for item in mappings
            }
            self._fill_blocks(selected_block)
            self._fill_parameters()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się pobrać mapowań rodzajów wizyt:\n\n{exc}",
            )

    def _fill_blocks(self, selected_block=None):
        self.blocks_table.setRowCount(len(self._blocks))
        selected_row = 0 if self._blocks else -1
        for row, block in enumerate(self._blocks):
            values = (
                block["nazwa"],
                block["grupa_nazwa"],
                block["liczba_mapowan"],
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value or ""))
                if column == 0:
                    item.setData(
                        Qt.ItemDataRole.UserRole,
                        block["klocek_id"],
                    )
                    color = QColor(str(block.get("kolor") or ""))
                    text_color = QColor(
                        str(block.get("kolor_tekstu") or "")
                    )
                    if color.isValid():
                        item.setBackground(color)
                    if text_color.isValid():
                        item.setForeground(text_color)
                self.blocks_table.setItem(row, column, item)
            if block["klocek_id"] == selected_block:
                selected_row = row
        if selected_row >= 0:
            self.blocks_table.selectRow(selected_row)

    def _fill_parameters(self):
        parameters_by_code = {
            str(parameter.code).strip().upper(): parameter
            for parameter in self._parameters
        }
        if not self.only_active_checkbox.isChecked():
            for code, mapping in self._mappings_by_code.items():
                if code not in parameters_by_code:
                    parameters_by_code[code] = VisitParameter(
                        code=code,
                        name=mapping["parametr_nazwa_cache"],
                        is_active=None,
                    )

        parameters = sorted(
            parameters_by_code.values(),
            key=lambda item: (
                str(item.name or "").casefold(),
                str(item.code).casefold(),
            ),
        )
        self.parameters_table.setRowCount(len(parameters))
        for row, parameter in enumerate(parameters):
            code = str(parameter.code).strip().upper()
            mapping = self._mappings_by_code.get(code)
            values = (
                code,
                parameter.name or "",
                self._active_text(parameter.is_active),
                mapping["klocek_nazwa"] if mapping else "Nie przypisano",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, code)
                    item.setData(
                        MAPPING_ID_ROLE,
                        mapping["mapowanie_id"] if mapping else None,
                    )
                    item.setData(
                        PARAMETER_NAME_ROLE,
                        parameter.name,
                    )
                self.parameters_table.setItem(row, column, item)

    def assign_selected(self):
        block_id = self.selected_block_id()
        rows = self.selected_parameter_rows()
        if block_id is None or not rows:
            QMessageBox.information(
                self,
                "KOMPAS",
                "Wybierz klocek oraz co najmniej jeden rodzaj wizyty.",
            )
            return
        try:
            for row in rows:
                item = self.parameters_table.item(row, 0)
                assign_visit_parameter(
                    block_id,
                    item.data(Qt.ItemDataRole.UserRole),
                    item.data(PARAMETER_NAME_ROLE),
                )
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się zapisać mapowania:\n\n{exc}",
            )

    def remove_selected(self):
        mapping_ids = []
        for row in self.selected_parameter_rows():
            item = self.parameters_table.item(row, 0)
            mapping_id = item.data(MAPPING_ID_ROLE)
            if mapping_id is not None:
                mapping_ids.append(mapping_id)
        if not mapping_ids:
            QMessageBox.information(
                self,
                "KOMPAS",
                "Zaznaczone rodzaje wizyt nie mają przypisania.",
            )
            return
        try:
            for mapping_id in mapping_ids:
                delete_visit_mapping(mapping_id)
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się usunąć mapowania:\n\n{exc}",
            )
