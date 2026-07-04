from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.gateway.eskulap_gateway import EskulapGateway
from app.repositories.pathway_unit_repository import (
    assign_unit_to_pathway,
    list_pathway_units,
    remove_unit_from_pathway,
)
from app.repositories.program_unit_repository import (
    assign_unit_to_program,
    list_program_units,
    remove_unit_from_program,
)
from app.repositories.user_unit_repository import (
    assign_unit_to_user,
    list_user_units,
    remove_unit_from_user,
    set_default_unit,
)
from app.ui.ui_helpers import (
    ask_confirmation,
    create_help_button,
    polish_dialog_buttons,
)
from app.ui.widgets.busy_indicator import busy_operation


TARGETS = {
    "user": {
        "title": "Jednostki organizacyjne użytkownika",
        "list": list_user_units,
        "assign": assign_unit_to_user,
        "remove": remove_unit_from_user,
    },
    "program": {
        "title": "Jednostki organizacyjne programu",
        "list": list_program_units,
        "assign": assign_unit_to_program,
        "remove": remove_unit_from_program,
    },
    "pathway": {
        "title": "Jednostki organizacyjne ścieżki",
        "list": list_pathway_units,
        "assign": assign_unit_to_pathway,
        "remove": remove_unit_from_pathway,
    },
}


class UnitAssignmentsDialog(QDialog):
    def __init__(self, target_type, target_id, parent=None):
        super().__init__(parent)
        if target_type not in TARGETS:
            raise ValueError("Nieznany typ przypisania jednostki")
        self.target_type = target_type
        self.target_id = target_id
        self.target = TARGETS[target_type]
        self.setWindowTitle(f"KOMPAS — {self.target['title']}")
        self.resize(780, 480)

        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 4 if target_type == "user" else 3)
        headers = ["JO ID", "Symbol", "Nazwa"]
        if target_type == "user":
            headers.append("Domyślna")
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.Stretch,
        )
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        self.add_button = QPushButton("Dodaj")
        self.remove_button = QPushButton("Usuń")
        self.default_button = QPushButton("Ustaw jako domyślną")
        self.default_button.setVisible(target_type == "user")
        self.help_button = create_help_button(
            self,
            self.target["title"],
            "To okno służy do przypisywania jednostek organizacyjnych.\n\n"
            "Możesz dodać jednostkę z Eskulapa, usunąć przypisanie, a dla "
            "użytkownika także wskazać jednostkę domyślną.\n\n"
            "Nie usuwaj przypisania bez upewnienia się, że użytkownik lub "
            "konfiguracja nie wymaga tej jednostki.",
        )
        self.add_button.setToolTip(
            "Wyszukaj w Eskulapie i dodaj jednostkę organizacyjną."
        )
        self.remove_button.setToolTip("Usuń zaznaczone przypisanie.")
        self.default_button.setToolTip(
            "Ustaw zaznaczoną jednostkę jako domyślną użytkownika."
        )
        actions.addWidget(self.add_button)
        actions.addWidget(self.remove_button)
        actions.addWidget(self.default_button)
        actions.addWidget(self.help_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        polish_dialog_buttons(buttons)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.add_button.clicked.connect(self.add_unit)
        self.remove_button.clicked.connect(self.remove_unit)
        self.default_button.clicked.connect(self.make_default)
        self.refresh_units()

    def selected_unit_id(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def refresh_units(self):
        try:
            units = self.target["list"](self.target_id)
            self.table.setRowCount(len(units))
            for row_index, unit in enumerate(units):
                values = [
                    unit["jo_id"],
                    unit["jo_symbol"] or "",
                    unit["jo_nazwa"] or "",
                ]
                if self.target_type == "user":
                    values.append("Tak" if unit["is_default"] else "Nie")
                for column_index, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    if column_index == 0:
                        item.setData(
                            Qt.ItemDataRole.UserRole,
                            str(unit["jo_id"]),
                        )
                    self.table.setItem(row_index, column_index, item)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się pobrać przypisanych jednostek:\n\n{exc}",
            )

    def add_unit(self):
        search_text, accepted = QInputDialog.getText(
            self,
            "KOMPAS — Wyszukaj jednostkę",
            "Symbol, nazwa lub identyfikator jednostki (opcjonalnie):",
        )
        if not accepted:
            return
        try:
            with busy_operation(
                self,
                "Trwa pobieranie jednostek organizacyjnych z Eskulapa...",
            ):
                units = EskulapGateway().list_organizational_units(
                    search_text
                )
            if not units:
                QMessageBox.information(
                    self,
                    "KOMPAS",
                    "Nie znaleziono jednostek spełniających kryterium.",
                )
                return
            labels = [unit.display_name for unit in units]
            selected_label, selected = QInputDialog.getItem(
                self,
                "KOMPAS — Wybierz jednostkę",
                "Jednostka organizacyjna:",
                labels,
                0,
                False,
            )
            if not selected:
                return
            unit = units[labels.index(selected_label)]
            self.target["assign"](
                self.target_id,
                unit.jo_id,
                unit.jo_symbol,
                unit.jo_nazwa,
            )
            self.refresh_units()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się przypisać jednostki:\n\n{exc}",
            )

    def remove_unit(self):
        jo_id = self.selected_unit_id()
        if jo_id is None:
            QMessageBox.information(
                self,
                "KOMPAS",
                "Wybierz jednostkę do usunięcia.",
            )
            return
        if not ask_confirmation(
            self,
            "Czy na pewno usunąć wybrane przypisanie jednostki?",
        ):
            return
        try:
            self.target["remove"](self.target_id, jo_id)
            self.refresh_units()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się usunąć przypisania:\n\n{exc}",
            )

    def make_default(self):
        jo_id = self.selected_unit_id()
        if jo_id is None:
            QMessageBox.information(
                self,
                "KOMPAS",
                "Wybierz jednostkę domyślną.",
            )
            return
        try:
            set_default_unit(self.target_id, jo_id)
            self.refresh_units()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się ustawić jednostki domyślnej:\n\n{exc}",
            )
