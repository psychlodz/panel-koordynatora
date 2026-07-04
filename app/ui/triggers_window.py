from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.repositories.pathway_repository import list_pathway_elements
from app.repositories.trigger_repository import (
    create_trigger,
    delete_trigger as remove_trigger,
    list_triggers,
    update_trigger,
)
from app.ui.ui_helpers import (
    ask_confirmation,
    create_help_button,
    polish_dialog_buttons,
)


TRIGGER_TYPE_LABELS = {
    "START_EPIZODU": "Start epizodu",
    "PO_ZAKONCZENIU": "Po zakończeniu elementu",
    "PO_ZLECENIU": "Po zleceniu",
    "PO_WYNIKU": "Po otrzymaniu wyniku",
    "RECZNIE": "Ręcznie",
}


class TriggerDialog(QDialog):
    def __init__(self, element, trigger=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(
            "KOMPAS — Edytuj wyzwalacz"
            if trigger
            else "KOMPAS — Dodaj wyzwalacz"
        )
        self.resize(620, 360)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.type_combo = QComboBox()
        for code, label in TRIGGER_TYPE_LABELS.items():
            self.type_combo.addItem(label, code)
        self.source_combo = QComboBox()
        self.source_combo.addItem("Brak elementu źródłowego", None)
        self.description_edit = QTextEdit()

        pathway_elements = list_pathway_elements(element["sciezka_id"])
        for source in pathway_elements:
            label = f"{source['lp']}. {source['nazwa_w_sciezce']} [{source['klocek_kod']}]"
            self.source_combo.addItem(label, source["element_id"])

        form.addRow("Typ:", self.type_combo)
        form.addRow("Element źródłowy:", self.source_combo)
        form.addRow("Opis:", self.description_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        polish_dialog_buttons(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if trigger is not None:
            type_index = self.type_combo.findData(trigger["trigger_type"])
            if type_index >= 0:
                self.type_combo.setCurrentIndex(type_index)
            source_index = self.source_combo.findData(
                trigger["trigger_element_id"]
            )
            if source_index >= 0:
                self.source_combo.setCurrentIndex(source_index)
            self.description_edit.setPlainText(trigger["opis"] or "")

        self.type_combo.currentTextChanged.connect(self.update_source_state)
        self.update_source_state()

    def update_source_state(self, _value=None):
        is_episode_start = self.type_combo.currentData() == "START_EPIZODU"
        if is_episode_start:
            self.source_combo.setCurrentIndex(0)
        self.source_combo.setEnabled(not is_episode_start)

    def values(self) -> dict:
        return {
            "trigger_type": self.type_combo.currentData(),
            "trigger_element_id": self.source_combo.currentData(),
            "opis": self.description_edit.toPlainText().strip() or None,
        }


class TriggersWindow(QWidget):
    def __init__(self, element):
        super().__init__()
        self.element = element
        self.element_id = element["element_id"]
        self._triggers_by_id = {}
        self.setWindowTitle("KOMPAS — Wyzwalacze")
        self.resize(900, 520)

        layout = QVBoxLayout(self)
        title = QLabel(
            f"Wyzwalacze elementu: {element['lp']}. {element['nazwa_w_sciezce']}"
        )
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(
            ["Typ", "Element źródłowy", "Opis"]
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
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table, 1)

        buttons = QHBoxLayout()
        self.add_button = QPushButton("Dodaj")
        self.edit_button = QPushButton("Edytuj")
        self.delete_button = QPushButton("Usuń")
        self.refresh_button = QPushButton("Odśwież")
        self.help_button = create_help_button(
            self,
            "Wyzwalacze",
            "To okno określa, kiedy element ścieżki zostaje aktywowany.\n\n"
            "Możesz dodawać, edytować i usuwać wyzwalacze elementu.\n\n"
            "Nie dodawaj kilku wyzwalaczy START_EPIZODU dla tego samego "
            "elementu.",
        )
        self.add_button.setToolTip("Dodaj nowy wyzwalacz elementu.")
        self.edit_button.setToolTip("Edytuj zaznaczony wyzwalacz.")
        self.delete_button.setToolTip("Usuń zaznaczony wyzwalacz.")
        self.refresh_button.setToolTip("Pobierz ponownie listę wyzwalaczy.")
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.edit_button)
        buttons.addWidget(self.delete_button)
        buttons.addWidget(self.refresh_button)
        buttons.addWidget(self.help_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.add_button.clicked.connect(self.add_trigger)
        self.edit_button.clicked.connect(self.edit_trigger)
        self.delete_button.clicked.connect(self.delete_trigger)
        self.refresh_button.clicked.connect(lambda: self.refresh_triggers())

        self.refresh_triggers()

    def _show_error(self, message, exc):
        QMessageBox.critical(self, "KOMPAS", f"{message}: {exc}")

    def current_trigger_id(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def refresh_triggers(self):
        try:
            triggers = list_triggers(self.element_id)
            self._triggers_by_id = {
                trigger["trigger_id"]: trigger for trigger in triggers
            }
            self.table.setRowCount(len(triggers))
            for row_index, trigger in enumerate(triggers):
                if trigger["trigger_element_id"] is None:
                    source = "—"
                else:
                    source = (
                        f"{trigger['trigger_element_lp']}. "
                        f"{trigger['trigger_element_nazwa']}"
                    )
                values = [
                    TRIGGER_TYPE_LABELS.get(
                        trigger["trigger_type"],
                        trigger["trigger_type"],
                    ),
                    source,
                    trigger["opis"] or "",
                ]
                for column_index, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    if column_index == 0:
                        item.setData(
                            Qt.ItemDataRole.UserRole, trigger["trigger_id"]
                        )
                    self.table.setItem(row_index, column_index, item)
        except Exception as exc:
            self._show_error("Nie udało się pobrać wyzwalaczy", exc)

    def add_trigger(self):
        try:
            dialog = TriggerDialog(self.element, parent=self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            create_trigger(self.element_id, **dialog.values())
            self.refresh_triggers()
        except Exception as exc:
            self._show_error("Nie udało się dodać wyzwalacza", exc)

    def edit_trigger(self):
        trigger_id = self.current_trigger_id()
        if trigger_id is None:
            QMessageBox.information(
                self, "KOMPAS", "Wybierz wyzwalacz do edycji."
            )
            return
        trigger = self._triggers_by_id.get(trigger_id)
        if trigger is None:
            self.refresh_triggers()
            return
        try:
            dialog = TriggerDialog(self.element, trigger=trigger, parent=self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            update_trigger(trigger_id, **dialog.values())
            self.refresh_triggers()
        except Exception as exc:
            self._show_error("Nie udało się zaktualizować wyzwalacza", exc)

    def delete_trigger(self):
        trigger_id = self.current_trigger_id()
        if trigger_id is None:
            QMessageBox.information(
                self, "KOMPAS", "Wybierz wyzwalacz do usunięcia."
            )
            return
        if not ask_confirmation(
            self,
            "Czy na pewno usunąć wybrany wyzwalacz?",
        ):
            return
        try:
            remove_trigger(trigger_id)
            self.refresh_triggers()
        except Exception as exc:
            self._show_error("Nie udało się usunąć wyzwalacza", exc)
