from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.repositories.visit_mapping_repository import (
    VisitTypeMappingConflict,
    assign_visit_types,
    list_blocks_with_visit_types,
    remove_mappings,
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
MAPPED_BLOCK_ID_ROLE = int(Qt.ItemDataRole.UserRole) + 6
BLOCK_ROLE = int(Qt.ItemDataRole.UserRole) + 20

DESCRIPTION = (
    "Mapowanie rodzajów wizyt określa, jaki klocek procesu KOMPAS odpowiada "
    "danemu rodzajowi wizyty z systemu Eskulap (WP_PARAMETR). Jeden klocek "
    "może być powiązany z wieloma rodzajami wizyt."
)

HELP_TEXT = (
    f"{DESCRIPTION}\n\n"
    "Po lewej wybierz jeden klocek KOMPAS. Po prawej zaznacz wszystkie "
    "rodzaje wizyt Eskulapa, które mają odpowiadać temu klockowi. "
    "Zapis odbywa się jedną transakcją. Jeden rodzaj wizyty może mieć tylko "
    "jedno aktywne przypisanie do klocka."
)


class VisitMappingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._blocks = []
        self._visit_types = []
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        description = QLabel(DESCRIPTION)
        description.setWordWrap(True)
        description.setObjectName("settingsTabDescription")
        layout.addWidget(description)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        left_panel = QWidget(splitter)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.addWidget(QLabel("Klocki KOMPAS"))
        self.blocks_list = QListWidget()
        self.blocks_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.blocks_list.setAlternatingRowColors(True)
        self.blocks_list.setWordWrap(True)
        left_layout.addWidget(self.blocks_list, 1)

        right_panel = QWidget(splitter)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 0, 0, 0)

        filters = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(
            [
                "Wszystkie",
                "Aktualne w Eskulapie",
                "Nieaktualne w Eskulapie",
                "Przypisane do wybranego klocka",
                "Nieprzypisane",
            ]
        )
        self.search_edit = QLineEdit()
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setPlaceholderText(
            "Szukaj po kodzie, nazwie, klocku lub typie..."
        )
        self.assigned_count_label = QLabel("Przypisane rodzaje wizyt: 0")
        filters.addWidget(QLabel("Filtr:"))
        filters.addWidget(self.filter_combo)
        filters.addWidget(QLabel("Wyszukiwarka:"))
        filters.addWidget(self.search_edit, 1)
        filters.addWidget(self.assigned_count_label)
        right_layout.addLayout(filters)

        self.visit_types_list = QListWidget()
        self.visit_types_list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.visit_types_list.setAlternatingRowColors(True)
        self.visit_types_list.setWordWrap(True)
        right_layout.addWidget(QLabel("Rodzaje wizyt Eskulapa"))
        right_layout.addWidget(self.visit_types_list, 1)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([320, 780])

        actions = QHBoxLayout()
        self.sync_button = QPushButton("Synchronizuj z Eskulapem")
        self.sync_button.setToolTip(
            "Pobierz aktualny słownik rodzajów wizyt z Eskulapa do PostgreSQL."
        )
        self.save_button = QPushButton("Zapisz mapowania")
        self.save_button.setToolTip(
            "Zapisz wszystkie zaznaczone rodzaje wizyt dla wybranego klocka."
        )
        self.remove_button = QPushButton("Usuń zaznaczone przypisania")
        self.remove_button.setToolTip(
            "Usuń aktywne mapowania zaznaczonych rodzajów wizyt."
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
        actions.addWidget(self.save_button)
        actions.addWidget(self.remove_button)
        actions.addWidget(self.active_button)
        actions.addWidget(self.refresh_button)
        actions.addStretch(1)
        actions.addWidget(self.help_button)
        layout.addLayout(actions)

        self.sync_button.clicked.connect(self.synchronize)
        self.refresh_button.clicked.connect(self.refresh)
        self.save_button.clicked.connect(self.save_mappings)
        self.remove_button.clicked.connect(self.remove_selected)
        self.active_button.clicked.connect(self.toggle_kompas_active)
        self.filter_combo.currentIndexChanged.connect(self.apply_filter)
        self.search_edit.textChanged.connect(self.apply_filter)
        self.blocks_list.currentItemChanged.connect(self._selected_block_changed)
        self.visit_types_list.itemChanged.connect(self._visit_type_check_changed)

        QTimer.singleShot(0, self.refresh)

    def _selected_block(self):
        item = self.blocks_list.currentItem()
        if item is None:
            return None
        return item.data(BLOCK_ROLE)

    def _selected_block_id(self):
        block = self._selected_block()
        if not block:
            return None
        return int(block["klocek_id"])

    def _selected_visit_items(self):
        return [
            item
            for item in self.visit_types_list.selectedItems()
            if item.data(VISIT_TYPE_ID_ROLE) is not None
        ]

    @staticmethod
    def _yes_no(value):
        return "Tak" if int(value or 0) == 1 else "Nie"

    def refresh(self):
        try:
            current_block_id = self._selected_block_id()
            with busy_operation(
                self,
                "Trwa pobieranie lokalnego słownika rodzajów wizyt...",
            ):
                self._blocks = list_blocks_with_visit_types(only_active=True)
                self._visit_types = list_visit_types(active_only=False)
            self._fill_blocks(current_block_id)
            self._fill_visit_types()
            self._update_checks_for_selected_block()
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

    def _fill_blocks(self, preferred_block_id=None):
        self.blocks_list.clear()
        selected_row = 0
        for row, block in enumerate(self._blocks):
            count = int(block.get("liczba_mapowan") or 0)
            item = QListWidgetItem(
                f"{block.get('nazwa')}\n"
                f"{block.get('typ_nazwa') or 'bez typu'} • "
                f"przypisań: {count}"
            )
            item.setData(BLOCK_ROLE, block)
            tooltip = (
                f"{block.get('kod')}\n"
                f"Typ: {block.get('typ_nazwa') or 'bez typu'}\n"
                f"Przypisane rodzaje wizyt: {count}"
            )
            item.setToolTip(tooltip)
            if block.get("kolor"):
                background = QColor(str(block.get("kolor")))
                foreground = QColor(str(block.get("kolor_tekstu") or ""))
                apply_readable_item_colors(item, background, foreground)
            self.blocks_list.addItem(item)
            if preferred_block_id and int(block["klocek_id"]) == int(preferred_block_id):
                selected_row = row
        if self.blocks_list.count() > 0:
            self.blocks_list.setCurrentRow(selected_row)

    def _fill_visit_types(self):
        self._loading = True
        try:
            self.visit_types_list.clear()
            for visit_type in self._visit_types:
                code = str(visit_type.get("parametr_kod") or "")
                name = str(visit_type.get("parametr_nazwa") or "")
                mapped_block = str(visit_type.get("klocek_nazwa") or "")
                block_type = str(visit_type.get("typ_nazwa") or "")
                mapped_info = (
                    f" → {mapped_block} ({block_type or 'bez typu'})"
                    if mapped_block
                    else " → nieprzypisany"
                )
                item = QListWidgetItem(f"{code} — {name}{mapped_info}")
                item.setFlags(
                    item.flags()
                    | Qt.ItemFlag.ItemIsUserCheckable
                    | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsEnabled
                )
                item.setCheckState(Qt.CheckState.Unchecked)
                item.setData(
                    VISIT_TYPE_ID_ROLE,
                    visit_type.get("rodzaj_wizyty_id"),
                )
                item.setData(MAPPING_ID_ROLE, visit_type.get("mapowanie_id"))
                item.setData(CODE_ROLE, code)
                item.setData(PARAMETER_NAME_ROLE, name)
                item.setData(
                    KOMPAS_ACTIVE_ROLE,
                    int(visit_type.get("czy_aktywny_kompas") or 0),
                )
                item.setData(
                    MAPPED_BLOCK_ID_ROLE,
                    visit_type.get("klocek_id"),
                )
                item.setToolTip(
                    f"Kod: {code}\n"
                    f"Nazwa: {name}\n"
                    f"Aktualny w Eskulapie: "
                    f"{self._yes_no(visit_type.get('czy_aktualny_eskulap'))}\n"
                    f"Aktywny w KOMPAS: "
                    f"{self._yes_no(visit_type.get('czy_aktywny_kompas'))}\n"
                    f"Przypisanie: {mapped_block or 'brak'}"
                )
                self.visit_types_list.addItem(item)
        finally:
            self._loading = False

    def _selected_block_changed(self, *_args):
        self._update_checks_for_selected_block()
        self.apply_filter()

    def _update_checks_for_selected_block(self):
        block_id = self._selected_block_id()
        count = 0
        self._loading = True
        try:
            for row in range(self.visit_types_list.count()):
                item = self.visit_types_list.item(row)
                mapped_block_id = item.data(MAPPED_BLOCK_ID_ROLE)
                checked = (
                    block_id is not None
                    and mapped_block_id is not None
                    and int(mapped_block_id) == int(block_id)
                )
                item.setCheckState(
                    Qt.CheckState.Checked
                    if checked
                    else Qt.CheckState.Unchecked
                )
                if checked:
                    count += 1
        finally:
            self._loading = False
        self.assigned_count_label.setText(
            f"Przypisane rodzaje wizyt: {count}"
        )

    def _visit_type_check_changed(self, _item):
        if self._loading:
            return
        count = sum(
            1
            for row in range(self.visit_types_list.count())
            if self.visit_types_list.item(row).checkState()
            == Qt.CheckState.Checked
        )
        self.assigned_count_label.setText(
            f"Przypisane rodzaje wizyt: {count}"
        )

    def apply_filter(self):
        search = self.search_edit.text().strip().casefold()
        filter_text = self.filter_combo.currentText()
        block_id = self._selected_block_id()
        for row in range(self.visit_types_list.count()):
            item = self.visit_types_list.item(row)
            code = str(item.data(CODE_ROLE) or "")
            name = str(item.data(PARAMETER_NAME_ROLE) or "")
            mapped_block_id = item.data(MAPPED_BLOCK_ID_ROLE)
            is_current_block = (
                block_id is not None
                and mapped_block_id is not None
                and int(mapped_block_id) == int(block_id)
            )
            is_mapped = mapped_block_id is not None
            is_current = "Aktualny w Eskulapie: Tak" in item.toolTip()
            searchable = f"{code} {name} {item.text()}".casefold()
            hidden = bool(search and search not in searchable)
            if filter_text == "Aktualne w Eskulapie":
                hidden = hidden or not is_current
            elif filter_text == "Nieaktualne w Eskulapie":
                hidden = hidden or is_current
            elif filter_text == "Przypisane do wybranego klocka":
                hidden = hidden or not is_current_block
            elif filter_text == "Nieprzypisane":
                hidden = hidden or is_mapped
            item.setHidden(hidden)

    def _checked_visit_type_ids(self):
        result = []
        for row in range(self.visit_types_list.count()):
            item = self.visit_types_list.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                result.append(int(item.data(VISIT_TYPE_ID_ROLE)))
        return result

    def save_mappings(self):
        block = self._selected_block()
        if not block:
            QMessageBox.information(
                self,
                "KOMPAS",
                "Wybierz klocek KOMPAS.",
            )
            return
        visit_type_ids = self._checked_visit_type_ids()
        try:
            summary = assign_visit_types(
                block["klocek_id"],
                visit_type_ids,
                replace_conflicts=False,
            )
        except VisitTypeMappingConflict as exc:
            conflict = exc.conflicts[0]
            accepted = QMessageBox.question(
                self,
                "Rodzaj wizyty już przypisany",
                "Rodzaj wizyty "
                f"{conflict.get('parametr_kod')} jest już przypisany do "
                f"klocka {conflict.get('klocek_kod')}.\n\n"
                "Czy przenieść przypisanie do wybranego klocka?",
            )
            if accepted != QMessageBox.StandardButton.Yes:
                return
            try:
                summary = assign_visit_types(
                    block["klocek_id"],
                    visit_type_ids,
                    replace_conflicts=True,
                )
            except Exception as exc2:
                QMessageBox.critical(
                    self,
                    "KOMPAS",
                    f"Nie udało się zapisać mapowań:\n\n{exc2}",
                )
                return
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się zapisać mapowań:\n\n{exc}",
            )
            return

        QMessageBox.information(
            self,
            "Mapowania zapisane",
            "Zapisano mapowania: dodano {added}, usunięto {removed}.".format(
                **summary
            ),
        )
        self.refresh()

    def remove_selected(self):
        mapping_ids = [
            item.data(MAPPING_ID_ROLE)
            for item in self._selected_visit_items()
            if item.data(MAPPING_ID_ROLE) is not None
        ]
        if not mapping_ids:
            QMessageBox.information(
                self,
                "KOMPAS",
                "Zaznaczone rodzaje wizyt nie mają przypisania.",
            )
            return
        try:
            removed = remove_mappings(mapping_ids)
            QMessageBox.information(
                self,
                "Mapowania usunięte",
                f"Usunięto przypisania: {removed}.",
            )
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się usunąć mapowania:\n\n{exc}",
            )

    def toggle_kompas_active(self):
        items = self._selected_visit_items()
        if not items:
            QMessageBox.information(
                self,
                "KOMPAS",
                "Zaznacz rodzaj wizyty, którego aktywność chcesz zmienić.",
            )
            return
        try:
            for item in items:
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
