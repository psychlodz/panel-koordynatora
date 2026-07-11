from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
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

from app.repositories.visit_mapping_repository import (
    assign_visit_parameter,
    delete_visit_mapping,
    list_mapping_blocks,
)
from app.repositories.visit_type_dictionary_repository import (
    list_visit_types,
    set_kompas_active,
)
from app.services.visit_type_dictionary_sync_service import (
    synchronize_visit_type_dictionary,
)
from app.ui.theme.color_utils import apply_readable_item_colors
from app.ui.ui_helpers import create_help_button
from app.ui.widgets.busy_indicator import busy_operation


VISIT_TYPE_ID_ROLE = int(Qt.ItemDataRole.UserRole) + 1
MAPPING_ID_ROLE = int(Qt.ItemDataRole.UserRole) + 2
CODE_ROLE = int(Qt.ItemDataRole.UserRole) + 3
PARAMETER_NAME_ROLE = int(Qt.ItemDataRole.UserRole) + 4
KOMPAS_ACTIVE_ROLE = int(Qt.ItemDataRole.UserRole) + 5

DESCRIPTION = (
    "Mapowanie rodzajów wizyt określa, jaki klocek procesu KOMPAS odpowiada "
    "danemu rodzajowi wizyty z systemu Eskulap (WP_PARAMETR). Jeden klocek "
    "może być powiązany z wieloma rodzajami wizyt."
)

HELP_TEXT = (
    f"{DESCRIPTION}\n\n"
    "Najpierw zsynchronizuj lokalny słownik z Eskulapem. Kody i nazwy są "
    "tylko do odczytu. W KOMPAS można przypisać kod do klocka, usunąć "
    "przypisanie albo ukryć rodzaj wizyty po stronie KOMPAS."
)


class VisitMappingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._blocks = []
        self._visit_types = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        description = QLabel(DESCRIPTION)
        description.setWordWrap(True)
        description.setObjectName("settingsTabDescription")
        layout.addWidget(description)

        filters = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(
            [
                "Wszystkie",
                "Aktualne w Eskulapie",
                "Nieaktualne w Eskulapie",
                "Przypisane",
                "Nieprzypisane",
            ]
        )
        self.search_edit = QLineEdit()
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setPlaceholderText(
            "Szukaj po kodzie, nazwie, klocku lub grupie..."
        )
        self.search_edit.setMinimumWidth(320)
        filters.addWidget(QLabel("Filtr:"))
        filters.addWidget(self.filter_combo)
        filters.addWidget(QLabel("Wyszukiwarka:"))
        filters.addWidget(self.search_edit, 1)
        layout.addLayout(filters)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            [
                "Kod",
                "Nazwa w Eskulapie",
                "Aktualny w Eskulapie",
                "Aktywny w KOMPAS",
                "Przypisany klocek",
                "Ostatnia synchronizacja",
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
        self.table.setWordWrap(True)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(90)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 105)
        self.table.setColumnWidth(2, 145)
        self.table.setColumnWidth(3, 135)
        self.table.setColumnWidth(4, 260)
        self.table.setColumnWidth(5, 175)
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        self.sync_button = QPushButton("Synchronizuj z Eskulapem")
        self.sync_button.setToolTip(
            "Pobierz aktualny słownik rodzajów wizyt z Eskulapa do PostgreSQL."
        )
        self.assign_button = QPushButton("Przypisz")
        self.assign_button.setToolTip(
            "Przypisz zaznaczone rodzaje wizyt do wybranego klocka."
        )
        self.remove_button = QPushButton("Usuń przypisanie")
        self.remove_button.setToolTip(
            "Usuń mapowania zaznaczonych rodzajów wizyt."
        )
        self.active_button = QPushButton("Aktywuj / ukryj w KOMPAS")
        self.active_button.setToolTip(
            "Zmień lokalną aktywność zaznaczonego rodzaju wizyty w KOMPAS."
        )
        self.refresh_button = QPushButton("Odśwież")
        self.refresh_button.setToolTip(
            "Odśwież lokalny słownik i mapowania z PostgreSQL."
        )
        self.help_button = create_help_button(
            self,
            "Mapowanie rodzajów wizyt",
            HELP_TEXT,
        )
        actions.addWidget(self.sync_button)
        actions.addWidget(self.assign_button)
        actions.addWidget(self.remove_button)
        actions.addWidget(self.active_button)
        actions.addWidget(self.refresh_button)
        actions.addStretch(1)
        actions.addWidget(self.help_button)
        layout.addLayout(actions)

        self.sync_button.clicked.connect(self.synchronize)
        self.refresh_button.clicked.connect(self.refresh)
        self.filter_combo.currentIndexChanged.connect(self.apply_filter)
        self.search_edit.textChanged.connect(self.apply_filter)
        self.assign_button.clicked.connect(self.assign_selected)
        self.remove_button.clicked.connect(self.remove_selected)
        self.active_button.clicked.connect(self.toggle_kompas_active)
        QTimer.singleShot(0, self.refresh)

    def selected_rows(self):
        return sorted({index.row() for index in self.table.selectedIndexes()})

    @staticmethod
    def _yes_no(value):
        return "Tak" if int(value or 0) == 1 else "Nie"

    def refresh(self):
        try:
            with busy_operation(
                self,
                "Trwa pobieranie lokalnego słownika rodzajów wizyt...",
            ):
                self._blocks = list_mapping_blocks(only_active=True)
                self._visit_types = list_visit_types(active_only=False)
            self._fill_table()
            self.apply_filter()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                "Nie udało się pobrać słownika rodzajów wizyt:\n\n"
                f"{exc}",
            )

    def synchronize(self):
        accepted = QMessageBox.question(
            self,
            "Synchronizacja słownika",
            "Pobrać aktualny słownik rodzajów wizyt z Eskulapa?\n\n"
            "Operacja nie zmienia danych w Oracle.",
        )
        if accepted != QMessageBox.StandardButton.Yes:
            return
        try:
            self.sync_button.setEnabled(False)
            with busy_operation(
                self,
                "Synchronizacja rodzajów wizyt z Eskulapa...",
            ):
                summary = synchronize_visit_type_dictionary()
            QMessageBox.information(
                self,
                "Synchronizacja zakończona",
                "Pobrano: {pobrano}\n"
                "Dodano: {dodano}\n"
                "Zaktualizowano: {zaktualizowano}\n"
                "Bez zmian: {bez_zmian}\n"
                "Oznaczono jako nieaktualne: "
                "{oznaczono_jako_nieaktualne}".format(**summary),
            )
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                "Nie udało się zsynchronizować słownika rodzajów wizyt:\n\n"
                f"{exc}",
            )
        finally:
            self.sync_button.setEnabled(True)

    def _fill_table(self):
        self.table.setRowCount(len(self._visit_types))
        for row, visit_type in enumerate(self._visit_types):
            block_label = "Nie przypisano"
            if visit_type.get("klocek_nazwa"):
                block_label = (
                    f"{visit_type['klocek_nazwa']}"
                    f" ({visit_type.get('grupa_nazwa') or 'bez grupy'})"
                )
            values = (
                visit_type.get("parametr_kod") or "",
                visit_type.get("parametr_nazwa") or "",
                self._yes_no(visit_type.get("czy_aktualny_eskulap")),
                self._yes_no(visit_type.get("czy_aktywny_kompas")),
                block_label,
                visit_type.get("synchronized_at") or "",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(
                        VISIT_TYPE_ID_ROLE,
                        visit_type.get("rodzaj_wizyty_id"),
                    )
                    item.setData(
                        MAPPING_ID_ROLE,
                        visit_type.get("mapowanie_id"),
                    )
                    item.setData(CODE_ROLE, visit_type.get("parametr_kod"))
                    item.setData(
                        PARAMETER_NAME_ROLE,
                        visit_type.get("parametr_nazwa"),
                    )
                    item.setData(
                        KOMPAS_ACTIVE_ROLE,
                        int(visit_type.get("czy_aktywny_kompas") or 0),
                    )
                if column == 4 and visit_type.get("klocek_kolor"):
                    background = QColor(str(visit_type.get("klocek_kolor")))
                    foreground = QColor(
                        str(visit_type.get("klocek_kolor_tekstu") or "")
                    )
                    apply_readable_item_colors(item, background, foreground)
                self.table.setItem(row, column, item)
        self.table.resizeRowsToContents()

    def apply_filter(self):
        search = self.search_edit.text().strip().casefold()
        filter_text = self.filter_combo.currentText()
        for row in range(self.table.rowCount()):
            code_item = self.table.item(row, 0)
            if code_item is None:
                continue
            mapping_id = code_item.data(MAPPING_ID_ROLE)
            is_current = self.table.item(row, 2).text() == "Tak"
            is_mapped = mapping_id is not None
            searchable = " ".join(
                self.table.item(row, column).text()
                for column in range(self.table.columnCount())
                if self.table.item(row, column) is not None
            ).casefold()
            hidden = bool(search and search not in searchable)
            if filter_text == "Aktualne w Eskulapie":
                hidden = hidden or not is_current
            elif filter_text == "Nieaktualne w Eskulapie":
                hidden = hidden or is_current
            elif filter_text == "Przypisane":
                hidden = hidden or not is_mapped
            elif filter_text == "Nieprzypisane":
                hidden = hidden or is_mapped
            self.table.setRowHidden(row, hidden)

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
                    item.data(CODE_ROLE),
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

    def toggle_kompas_active(self):
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(
                self,
                "KOMPAS",
                "Zaznacz rodzaj wizyty, którego aktywność chcesz zmienić.",
            )
            return
        try:
            for row in rows:
                item = self.table.item(row, 0)
                current = int(item.data(KOMPAS_ACTIVE_ROLE) or 0)
                set_kompas_active(
                    item.data(VISIT_TYPE_ID_ROLE),
                    active=current == 0,
                )
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się zmienić aktywności:\n\n{exc}",
            )
