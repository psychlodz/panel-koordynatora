from PySide6.QtCore import QSize, Qt, Signal, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
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
        title.setWordWrap(False)
        content.addWidget(title)

        block = QLabel(
            f"{element.get('klocek_nazwa') or 'Klocek'} "
            f"[{element.get('klocek_kod') or '—'}] • "
            f"{element.get('klocek_typ_nazwa') or 'bez typu'} • "
            f"{element.get('klocek_grupa_nazwa') or 'bez grupy'}"
        )
        block.setObjectName("tileMetadata")
        block.setWordWrap(False)
        color = element.get("klocek_kolor")
        if color:
            block.setStyleSheet(
                f"border-left: 6px solid {color}; padding-left: 6px;"
            )
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
        details.setWordWrap(False)
        content.addWidget(details)
        layout.addLayout(content, 1)

        base_color = QColor(str(element.get("klocek_kolor") or ""))
        text_color = QColor(
            str(element.get("klocek_kolor_tekstu") or "")
        )
        if base_color.isValid():
            if not text_color.isValid():
                text_color = QColor("#FFFFFF")
            base = base_color.name()
            foreground = text_color.name()
            self.setStyleSheet(
                f"""
                QFrame#pathwayTile {{
                    background-color: {base};
                    border: 2px solid {base_color.darker(135).name()};
                    border-radius: 10px;
                }}
                QFrame#pathwayTile[selected="true"] {{
                    border: 4px solid #0A2239;
                }}
                """
            )
            for label in (title, block, details):
                label.setStyleSheet(f"color: {foreground};")
            type_label.setStyleSheet(
                f"color: {base}; background-color: {foreground}; "
                "border-radius: 5px; padding: 3px; font-weight: 700;"
            )
            position.setStyleSheet(
                f"color: {base}; background-color: {foreground}; "
                "border-radius: 6px; font-weight: 700;"
            )

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
        self.setDropIndicatorShown(False)
        self.setAutoScroll(False)
        self.setSpacing(8)
        self.setAlternatingRowColors(False)
        self._drop_row = None
        self._scroll_direction = 0
        self._scroll_timer = QTimer(self)
        self._scroll_timer.setInterval(180)
        self._scroll_timer.timeout.connect(self._slow_auto_scroll)
        self.currentItemChanged.connect(self._selection_changed)
        self.itemDoubleClicked.connect(self._item_double_clicked)

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
        self._clear_drag_feedback()
        self._refresh_selection()
        if new_order != previous_order:
            self.orderChanged.emit(new_order)

    def dragEnterEvent(self, event):
        super().dragEnterEvent(event)
        if event.isAccepted():
            self._update_drag_feedback(event.position().toPoint())

    def dragMoveEvent(self, event):
        super().dragMoveEvent(event)
        if event.isAccepted():
            self._update_drag_feedback(event.position().toPoint())

    def dragLeaveEvent(self, event):
        self._clear_drag_feedback()
        super().dragLeaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._drop_row is None:
            return

        if self._drop_row >= self.count():
            if self.count():
                rect = self.visualItemRect(self.item(self.count() - 1))
                marker_y = rect.bottom() + self.spacing() // 2
            else:
                marker_y = 10
        else:
            rect = self.visualItemRect(self.item(self._drop_row))
            marker_y = rect.top() - self.spacing() // 2

        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor("#0B6FA4")
        painter.setPen(
            QPen(
                color,
                4,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
            )
        )
        margin = 14
        painter.drawLine(
            margin,
            marker_y,
            max(margin, self.viewport().width() - margin),
            marker_y,
        )
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(margin - 5, marker_y - 5, 10, 10)
        painter.drawEllipse(
            self.viewport().width() - margin - 5,
            marker_y - 5,
            10,
            10,
        )

    def _update_drag_feedback(self, position):
        item = self.itemAt(position)
        if item is None:
            drop_row = self.count()
        else:
            row = self.row(item)
            item_rect = self.visualItemRect(item)
            drop_row = row + (position.y() >= item_rect.center().y())

        if drop_row != self._drop_row:
            self._drop_row = drop_row
            self.viewport().update()

        edge = 36
        if position.y() < edge:
            direction = -1
        elif position.y() > self.viewport().height() - edge:
            direction = 1
        else:
            direction = 0
        self._set_scroll_direction(direction)

    def _set_scroll_direction(self, direction):
        self._scroll_direction = direction
        if direction:
            if not self._scroll_timer.isActive():
                self._scroll_timer.start()
        else:
            self._scroll_timer.stop()

    def _slow_auto_scroll(self):
        if not self._scroll_direction:
            return
        scrollbar = self.verticalScrollBar()
        step = max(1, scrollbar.singleStep())
        scrollbar.setValue(
            scrollbar.value() + self._scroll_direction * step
        )
        self.viewport().update()

    def _clear_drag_feedback(self):
        self._set_scroll_direction(0)
        if self._drop_row is not None:
            self._drop_row = None
            self.viewport().update()

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
