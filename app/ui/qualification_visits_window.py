import logging

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.repositories.pathway_repository import list_pathways
from app.repositories.program_repository import list_programs
from app.repositories.qualification_repository import (
    create_episode_from_qualification_visit,
    list_qualification_visits,
)
from app.services.work_context import work_context
from app.ui.ui_helpers import create_help_button, polish_dialog_buttons
from app.ui.widgets.busy_indicator import busy_operation
from version import APP_NAME


logger = logging.getLogger(__name__)


class QualificationAssignmentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(
            f"{APP_NAME} — Przypisz program i ścieżkę"
        )
        self.resize(560, 300)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.program_combo = QComboBox()
        self.pathway_combo = QComboBox()
        self.coordinator_edit = QLineEdit()
        self.coordinator_edit.setPlaceholderText(
            "Opcjonalny identyfikator koordynatora"
        )
        form.addRow("Program:", self.program_combo)
        form.addRow("Ścieżka:", self.pathway_combo)
        form.addRow("Koordynator:", self.coordinator_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        polish_dialog_buttons(buttons)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            "Utwórz epizod"
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        for program in list_programs():
            if program["czy_aktywny"]:
                self.program_combo.addItem(
                    program["nazwa"],
                    program["program_id"],
                )
        self.program_combo.currentIndexChanged.connect(
            self.load_pathways
        )
        self.load_pathways()

    def load_pathways(self):
        self.pathway_combo.clear()
        program_id = self.program_combo.currentData()
        if program_id is None:
            return
        for pathway in list_pathways(program_id):
            if pathway["czy_aktywna"]:
                self.pathway_combo.addItem(
                    pathway["nazwa"],
                    pathway["sciezka_id"],
                )

    def accept(self):
        if self.program_combo.currentData() is None:
            QMessageBox.warning(self, APP_NAME, "Wybierz program.")
            return
        if self.pathway_combo.currentData() is None:
            QMessageBox.warning(self, APP_NAME, "Wybierz ścieżkę.")
            return
        super().accept()

    def values(self):
        return {
            "program_id": self.program_combo.currentData(),
            "sciezka_id": self.pathway_combo.currentData(),
            "koordynator_id": (
                self.coordinator_edit.text().strip() or None
            ),
        }


class QualificationVisitsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            f"{APP_NAME} — Wizyty kwalifikacyjne PKK"
        )
        self.resize(1400, 720)
        self._visits = {}

        layout = QVBoxLayout(self)
        title = QLabel("Wizyty kwalifikacyjne PKK")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        filters = QHBoxLayout()
        today = QDate.currentDate()
        self.date_from = QDateEdit(today.addDays(-7))
        self.date_to = QDateEdit(today.addDays(7))
        self.date_from.setCalendarPopup(True)
        self.date_to.setCalendarPopup(True)
        filters.addWidget(QLabel("Od:"))
        filters.addWidget(self.date_from)
        filters.addWidget(QLabel("Do:"))
        filters.addWidget(self.date_to)
        filters.addStretch(1)
        self.refresh_button = QPushButton("Odśwież")
        self.refresh_button.setToolTip(
            "Pobierz ponownie nieprzypisane wizyty kwalifikacyjne."
        )
        filters.addWidget(self.refresh_button)
        layout.addLayout(filters)

        self.info_label = QLabel()
        layout.addWidget(self.info_label)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [
                "Data wizyty",
                "PESEL",
                "Nazwisko",
                "Imię",
                "Poradnia",
                "Pracownik",
                "Status przypisania",
            ]
        )
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
            4,
            QHeaderView.ResizeMode.Stretch,
        )
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        self.assign_button = QPushButton("Przypisz program/ścieżkę")
        self.help_button = create_help_button(
            self,
            "Wizyty kwalifikacyjne PKK",
            "To okno pokazuje nieprzypisane wizyty kwalifikacyjne PKK.\n\n"
            "Koordynator widzi wizyty swoich jednostek, a administrator "
            "wszystkie jednostki. Po utworzeniu epizodu wizyta znika z listy.",
        )
        self.close_button = QPushButton("Zamknij")
        self.assign_button.setToolTip(
            "Przypisz program, ścieżkę i koordynatora do zaznaczonej wizyty."
        )
        self.close_button.setToolTip(
            "Zamknij okno wizyt kwalifikacyjnych."
        )
        actions.addWidget(self.assign_button)
        actions.addWidget(self.help_button)
        actions.addStretch(1)
        actions.addWidget(self.close_button)
        layout.addLayout(actions)

        self.refresh_button.clicked.connect(self.refresh_visits)
        self.assign_button.clicked.connect(self.assign_selected_visit)
        self.close_button.clicked.connect(self.close)
        self.refresh_visits()

    def selected_visit(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        visit_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        if visit_id is None:
            QMessageBox.information(
                self,
                APP_NAME,
                "Wybierz wizytę kwalifikacyjną.",
            )
            return None
        return self._visits.get(str(visit_id))

    @staticmethod
    def _clinic_label(visit):
        symbol = str(visit.get("poradnia_symbol") or "").strip()
        name = str(
            visit.get("poradnia_nazwa")
            or visit.get("poradnia")
            or ""
        ).strip()
        return " - ".join(value for value in (symbol, name) if value)

    @staticmethod
    def _allowed_visits(visits):
        current_user = work_context.current_user
        if current_user is not None and current_user.is_admin:
            return visits
        allowed_units = {
            str(unit.jo_id)
            for unit in work_context.user_units
        }
        return [
            visit
            for visit in visits
            if str(visit.get("poradnia_id")) in allowed_units
        ]

    def refresh_visits(self):
        try:
            with busy_operation(
                self,
                "Trwa pobieranie wizyt kwalifikacyjnych z Oracle...",
            ):
                visits = list_qualification_visits(
                    self.date_from.date().toString("yyyy-MM-dd"),
                    self.date_to.date().toString("yyyy-MM-dd"),
                    only_unassigned=True,
                )
            visits = self._allowed_visits(visits)
            self._visits = {
                str(visit["wizyta_id"]): visit
                for visit in visits
            }
            self.table.setRowCount(len(visits))
            for row_index, visit in enumerate(visits):
                values = [
                    visit.get("data_wizyty") or visit.get("data_planowana"),
                    visit.get("pesel"),
                    visit.get("nazwisko"),
                    visit.get("imie"),
                    self._clinic_label(visit),
                    visit.get("pracownik"),
                    visit.get("assignment_status"),
                ]
                for column_index, value in enumerate(values):
                    item = QTableWidgetItem(
                        "" if value is None else str(value)
                    )
                    if column_index == 0:
                        item.setData(
                            Qt.ItemDataRole.UserRole,
                            visit["wizyta_id"],
                        )
                    self.table.setItem(
                        row_index,
                        column_index,
                        item,
                    )
            self.info_label.setText(f"Wizyty: {len(visits)}")
            logger.debug("REFRESH_OK visits=%s", len(visits))
            return True
        except Exception as exc:
            logger.debug("REFRESH_ERROR", exc_info=True)
            QMessageBox.critical(
                self,
                APP_NAME,
                "Nie udało się pobrać wizyt kwalifikacyjnych:\n\n"
                f"{exc}",
            )
            return False

    def assign_selected_visit(self):
        visit = self.selected_visit()
        if visit is None:
            return
        try:
            dialog = QualificationAssignmentDialog(self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            with busy_operation(
                self,
                "Trwa tworzenie epizodu i generowanie zadań...",
            ):
                episode_id = create_episode_from_qualification_visit(
                    visit["wizyta_id"],
                    **dialog.values(),
                )
            refresh_ok = self.refresh_visits()
            if not refresh_ok:
                raise RuntimeError(
                    "Epizod utworzono, ale nie udało się odświeżyć listy"
                )
            if str(visit["wizyta_id"]) in self._visits:
                raise RuntimeError(
                    "Epizod utworzono, ale wizyta nadal znajduje się "
                    "na liście nieprzypisanych"
                )
            QMessageBox.information(
                self,
                APP_NAME,
                f"Utworzono epizod {episode_id}.",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                APP_NAME,
                f"Nie udało się utworzyć epizodu:\n\n{exc}",
            )
