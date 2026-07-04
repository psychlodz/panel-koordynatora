from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)


class PathwayTile(QFrame):
    def __init__(self, element, parent=None):
        super().__init__(parent)
        self.setObjectName("pathwayTile")
        self.setProperty("selected", False)
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)

        marker = QVBoxLayout()
        marker.setSpacing(4)
        position = QLabel(str(element["lp"]))
        position.setObjectName("tilePosition")
        position.setAlignment(Qt.AlignmentFlag.AlignCenter)
        marker.addWidget(position)

        abbreviation = (
            element.get("klocek_ikona")
            or element.get("klocek_typ")
            or element.get("klocek_kod")
            or "—"
        )
        type_label = QLabel(str(abbreviation)[:8].upper())
        type_label.setObjectName("tileType")
        type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        marker.addWidget(type_label)
        layout.addLayout(marker)

        content = QVBoxLayout()
        content.setSpacing(4)
        title = QLabel(element["nazwa_w_sciezce"])
        title.setObjectName("tileTitle")
        title.setWordWrap(True)
        content.addWidget(title)

        block = QLabel(
            f"{element.get('klocek_nazwa') or 'Klocek'} "
            f"[{element.get('klocek_kod') or '—'}]"
        )
        block.setObjectName("tileMetadata")
        content.addWidget(block)

        maximum = (
            "bez limitu"
            if element["max_liczba"] is None
            else str(element["max_liczba"])
        )
        requirement = (
            "obowiązkowy"
            if element["czy_obowiazkowy"]
            else "opcjonalny"
        )
        details = QLabel(
            f"Min./maks.: {element['min_liczba']}/{maximum} • {requirement}"
        )
        details.setObjectName("tileDetails")
        content.addWidget(details)
        layout.addLayout(content, 1)

        self.setToolTip(
            "Kliknij, aby zaznaczyć. Przeciągnij kafelek, aby zmienić "
            "kolejność elementów."
        )

    def set_selected(self, selected):
        self.setProperty("selected", bool(selected))
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class PathwayTilesWidget(QListWidget):
    orderChanged = Signal(list)
    elementSelected = Signal(object)
    elementDoubleClicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pathwayTiles")
        self.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
        )
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setSpacing(8)
        self.setAlternatingRowColors(False)
        self.currentItemChanged.connect(self._selection_changed)
        self.itemDoubleClicked.connect(self._item_double_clicked)
        self.setStyleSheet(
            """
            QListWidget#pathwayTiles {
                background-color: #E9EFF5;
                border: 2px solid #8FA2B2;
                border-radius: 8px;
                padding: 8px;
            }
            QListWidget#pathwayTiles::item {
                background: transparent;
                border: none;
                padding: 0;
            }
            QListWidget#pathwayTiles::item:selected {
                background: transparent;
            }
            QFrame#pathwayTile {
                background-color: #FFFFFF;
                border: 2px solid #A9BAC8;
                border-radius: 10px;
            }
            QFrame#pathwayTile[selected="true"] {
                background-color: #E2F1FC;
                border: 3px solid #145A8D;
            }
            QLabel#tilePosition {
                min-width: 34px;
                min-height: 28px;
                color: #FFFFFF;
                background-color: #123B5D;
                border-radius: 6px;
                font-size: 11pt;
                font-weight: 700;
            }
            QLabel#tileType {
                min-width: 48px;
                color: #145A8D;
                background-color: #DCEAF5;
                border: 1px solid #8FAFC7;
                border-radius: 5px;
                padding: 3px;
                font-size: 8pt;
                font-weight: 700;
            }
            QLabel#tileTitle {
                color: #102A43;
                font-size: 11pt;
                font-weight: 700;
            }
            QLabel#tileMetadata {
                color: #334E68;
                font-size: 9pt;
            }
            QLabel#tileDetails {
                color: #526777;
                font-size: 9pt;
            }
            """
        )

    def set_elements(self, elements, selected_element_id=None):
        if selected_element_id is None:
            selected_element_id = self.selected_element_id()
        self.clear()
        for element in elements:
            item = QListWidgetItem()
            item.setData(
                Qt.ItemDataRole.UserRole,
                int(element["element_id"]),
            )
            item.setToolTip(
                "Kliknij, aby zaznaczyć. Przeciągnij kafelek, aby zmienić "
                "kolejność elementów."
            )
            item.setSizeHint(QSize(320, 112))
            self.addItem(item)
            self.setItemWidget(item, PathwayTile(element, self))
        self.select_element(selected_element_id)

    def ordered_element_ids(self):
        return [
            int(self.item(index).data(Qt.ItemDataRole.UserRole))
            for index in range(self.count())
        ]

    def selected_element_id(self):
        item = self.currentItem()
        if item is None:
            return None
        return int(item.data(Qt.ItemDataRole.UserRole))

    def select_element(self, element_id):
        if element_id is None:
            self.setCurrentRow(-1)
            self._refresh_selection()
            return
        for index in range(self.count()):
            item = self.item(index)
            if int(item.data(Qt.ItemDataRole.UserRole)) == int(element_id):
                self.setCurrentItem(item)
                self.scrollToItem(item)
                self._refresh_selection()
                return
        self.setCurrentRow(-1)
        self._refresh_selection()

    def dropEvent(self, event):
        previous_order = self.ordered_element_ids()
        super().dropEvent(event)
        new_order = self.ordered_element_ids()
        self._refresh_selection()
        if new_order != previous_order:
            self.orderChanged.emit(new_order)

    def _selection_changed(self, current, _previous):
        self._refresh_selection()
        element_id = (
            int(current.data(Qt.ItemDataRole.UserRole))
            if current is not None
            else None
        )
        self.elementSelected.emit(element_id)

    def _refresh_selection(self):
        current = self.currentItem()
        for index in range(self.count()):
            item = self.item(index)
            tile = self.itemWidget(item)
            if tile is not None:
                tile.set_selected(item is current)

    def _item_double_clicked(self, item, _column):
        self.elementDoubleClicked.emit(
            int(item.data(Qt.ItemDataRole.UserRole))
        )
