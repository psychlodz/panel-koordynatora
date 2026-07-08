from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
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
from app.models.visit_parameter import VisitParameter
from app.repositories.visit_mapping_repository import (
    assign_visit_parameter,
    delete_visit_mapping,
    list_mapping_blocks,
    list_visit_mappings,
)
from app.ui.theme.color_utils import apply_readable_item_colors
from app.ui.ui_helpers import create_help_button
from app.ui.widgets.busy_indicator import busy_operation


MAPPING_ID_ROLE = int(Qt.ItemDataRole.UserRole) + 1
PARAMETER_NAME_ROLE = int(Qt.ItemDataRole.UserRole) + 2
BLOCK_ID_ROLE = int(Qt.ItemDataRole.UserRole) + 3

DESCRIPTION = (
    "Mapowanie rodzajów wizyt określa, jaki klocek procesu KOMPAS "
    "odpowiada danemu rodzajowi wizyty z systemu Eskulap (WP_PARAMETR). "
    "Jeden klocek może być powiązany z wieloma rodzajami wizyt."
)

HELP_TEXT = (
    f"{DESCRIPTION}\n\n"
    "Zaznacz jeden lub kilka wierszy i wybierz „Przypisz”, aby wskazać "
    "klocek. „Usuń przypisanie” usuwa wyłącznie powiązanie w KOMPAS — "
    "nie modyfikuje danych Eskulapa."
)


class VisitMappingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._blocks = []
        self._blocks_by_id = {}
        self._parameters = []
        self._mappings_by_code = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        description = QLabel(DESCRIPTION)
        description.setWordWrap(True)
        description.setObjectName("settingsTabDescription")
        layout.addWidget(description)

        filters = QHBoxLayout()
        self.only_active_checkbox = QCheckBox("Tylko aktywne")
        self.only_active_checkbox.setChecked(True)
        self.search_edit = QLineEdit()
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setPlaceholderText(
            "Szukaj po kodzie, nazwie, klocku lub grupie..."
        )
        self.search_edit.setMinimumWidth(320)
        filters.addWidget(self.only_active_checkbox)
        filters.addWidget(QLabel("Wyszukiwarka:"))
        filters.addWidget(self.search_edit, 1)
        layout.addLayout(filters)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            [
                "Kod",
                "Nazwa rodzaju wizyty",
                "Klocek",
                "Grupa",
                "Status",
            ]
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(90)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 125)
        self.table.setColumnWidth(2, 230)
        self.table.setColumnWidth(3, 170)
        self.table.setColumnWidth(4, 110)
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        self.assign_button = QPushButton("Przypisz")
        self.assign_button.setToolTip(
            "Przypisz zaznaczone rodzaje wizyt do wybranego klocka."
        )
        self.remove_button = QPushButton("Usuń przypisanie")
        self.remove_button.setToolTip(
            "Usuń mapowania zaznaczonych rodzajów wizyt."
        )
        self.refresh_button = QPushButton("Odśwież")
        self.refresh_button.setToolTip(
            "Pobierz klocki z PostgreSQL i rodzaje wizyt z Eskulapa."
        )
        self.help_button = create_help_button(
            self,
            "Mapowanie rodzajów wizyt",
            HELP_TEXT,
        )
        actions.addWidget(self.assign_button)
        actions.addWidget(self.remove_button)
        actions.addWidget(self.refresh_button)
        actions.addStretch(1)
        actions.addWidget(self.help_button)
        layout.addLayout(actions)

        self.refresh_button.clicked.connect(self.refresh)
        self.only_active_checkbox.toggled.connect(self.refresh)
        self.search_edit.textChanged.connect(self.apply_filter)
        self.assign_button.clicked.connect(self.assign_selected)
        self.remove_button.clicked.connect(self.remove_selected)
        QTimer.singleShot(0, self.refresh)

    def selected_rows(self):
        return sorted({index.row() for index in self.table.selectedIndexes()})

    @staticmethod
    def _active_text(value):
        if value is None:
            return "Brak danych"
        return (
            "Aktywny"
            if str(value).strip().upper()
            in {"T", "TAK", "Y", "YES", "1", "TRUE"}
            else "Nieaktywny"
        )

    def refresh(self):
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
            self._blocks_by_id = {
                int(block["klocek_id"]): block
                for block in self._blocks
            }
            self._mappings_by_code = {
                str(item["parametr_kod"]).upper(): item
                for item in mappings
            }
            self._fill_table()
            self.apply_filter()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się pobrać mapowań rodzajów wizyt:\n\n{exc}",
            )

    def _all_parameters(self):
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
        return sorted(
            parameters_by_code.values(),
            key=lambda item: (
                str(item.name or "").casefold(),
                str(item.code).casefold(),
            ),
        )

    def _fill_table(self):
        parameters = self._all_parameters()
        self.table.setRowCount(len(parameters))
        for row, parameter in enumerate(parameters):
            code = str(parameter.code).strip().upper()
            mapping = self._mappings_by_code.get(code)
            block = (
                self._blocks_by_id.get(int(mapping["klocek_id"]))
                if mapping
                else None
            )
            values = (
                code,
                parameter.name or "",
                block["nazwa"] if block else "Nie przypisano",
                block["grupa_nazwa"] if block else "",
                self._active_text(parameter.is_active),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, code)
                    item.setData(
                        MAPPING_ID_ROLE,
                        mapping["mapowanie_id"] if mapping else None,
                    )
                    item.setData(PARAMETER_NAME_ROLE, parameter.name)
                    item.setData(
                        BLOCK_ID_ROLE,
                        mapping["klocek_id"] if mapping else None,
                    )
                if column == 2 and block:
                    background = QColor(str(block.get("kolor") or ""))
                    foreground = QColor(
                        str(block.get("kolor_tekstu") or "")
                    )
                    apply_readable_item_colors(item, background, foreground)
                self.table.setItem(row, column, item)

    def apply_filter(self):
        search = self.search_edit.text().strip().casefold()
        for row in range(self.table.rowCount()):
            searchable = " ".join(
                self.table.item(row, column).text()
                for column in range(self.table.columnCount())
                if self.table.item(row, column) is not None
            ).casefold()
            self.table.setRowHidden(
                row,
                bool(search and search not in searchable),
            )

    def _select_block(self):
        if not self._blocks:
            QMessageBox.information(
                self,
                "KOMPAS",
                "Brak aktywnych klocków możliwych do przypisania.",
            )
            return None
        options = [
            f"{block['nazwa']} — {block['grupa_nazwa']}"
            for block in self._blocks
        ]
        selected, accepted = QInputDialog.getItem(
            self,
            "Przypisz klocek",
            "Klocek KOMPAS:",
            options,
            0,
            False,
        )
        if not accepted:
            return None
        return self._blocks[options.index(selected)]

    def assign_selected(self):
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(
                self,
                "KOMPAS",
                "Zaznacz co najmniej jeden rodzaj wizyty.",
            )
            return
        block = self._select_block()
        if block is None:
            return
        try:
            for row in rows:
                item = self.table.item(row, 0)
                assign_visit_parameter(
                    block["klocek_id"],
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
        for row in self.selected_rows():
            mapping_id = self.table.item(row, 0).data(MAPPING_ID_ROLE)
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
