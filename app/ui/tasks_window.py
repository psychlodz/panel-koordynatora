from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateTimeEdit,
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
    QVBoxLayout,
    QWidget,
)

from app.repositories.patient_repository import get_patient
from app.repositories.task_repository import (
    cancel_task,
    list_active_tasks,
    schedule_task,
)
from episode_generator import complete_task


def _patient_name(patient, fallback):
    if patient:
        name = " ".join(
            part
            for part in (patient.get("nazwisko"), patient.get("imie"))
            if part
        ).strip()
        if name:
            return name
    return str(fallback)


class ScheduleTaskDialog(QDialog):
    def __init__(self, current_value=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("KOMPAS — Zaplanuj zadanie")

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.date_time_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.date_time_edit.setCalendarPopup(True)
        self.date_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        if current_value:
            parsed = QDateTime.fromString(
                str(current_value),
                Qt.DateFormat.ISODate,
            )
            if parsed.isValid():
                self.date_time_edit.setDateTime(parsed)
        form.addRow("Termin:", self.date_time_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def planned_at(self):
        return self.date_time_edit.dateTime().toString(Qt.DateFormat.ISODate)


class TasksWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KOMPAS — Aktywne zadania")
        self.resize(1250, 680)
        self._tasks = []
        self._tasks_by_id = {}
        self._patients = {}

        layout = QVBoxLayout(self)
        title = QLabel("Aktywne zadania")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        filters = QHBoxLayout()
        self.status_filter = QComboBox()
        self.coordinator_filter = QComboBox()
        self.program_filter = QComboBox()
        filters.addWidget(QLabel("Status:"))
        filters.addWidget(self.status_filter, 1)
        filters.addWidget(QLabel("Koordynator:"))
        filters.addWidget(self.coordinator_filter, 1)
        filters.addWidget(QLabel("Program:"))
        filters.addWidget(self.program_filter, 1)
        layout.addLayout(filters)

        self.info_label = QLabel()
        layout.addWidget(self.info_label)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Pacjent", "Zadanie", "Status", "Termin", "Program", "Ścieżka"]
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
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        self.schedule_button = QPushButton("Zaplanuj")
        self.complete_button = QPushButton("Zrealizowano")
        self.cancel_button = QPushButton("Anuluj")
        self.refresh_button = QPushButton("Odśwież")
        actions.addWidget(self.schedule_button)
        actions.addWidget(self.complete_button)
        actions.addWidget(self.cancel_button)
        actions.addStretch(1)
        actions.addWidget(self.refresh_button)
        layout.addLayout(actions)

        self.status_filter.currentIndexChanged.connect(self.apply_filters)
        self.coordinator_filter.currentIndexChanged.connect(self.apply_filters)
        self.program_filter.currentIndexChanged.connect(self.apply_filters)
        self.schedule_button.clicked.connect(self.schedule_selected_task)
        self.complete_button.clicked.connect(self.complete_selected_task)
        self.cancel_button.clicked.connect(self.cancel_selected_task)
        self.refresh_button.clicked.connect(self.refresh_tasks)

        self.refresh_tasks()

    @staticmethod
    def _set_combo_items(combo, items):
        selected = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Wszystkie", None)
        for text, value in items:
            combo.addItem(text, value)
        index = combo.findData(selected)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    def _refresh_filters(self):
        statuses = sorted({str(task["status"] or "") for task in self._tasks})
        coordinators = sorted(
            {str(task["koordynator_id"] or "") for task in self._tasks},
            key=str.casefold,
        )
        programs = {
            task["program_id"]: (
                task["program_nazwa"]
                or task["program_kod"]
                or str(task["program_id"])
            )
            for task in self._tasks
            if task["program_id"] is not None
        }
        self._set_combo_items(
            self.status_filter,
            [(value or "Brak statusu", value) for value in statuses],
        )
        self._set_combo_items(
            self.coordinator_filter,
            [
                (value or "Nie przypisano", value)
                for value in coordinators
            ],
        )
        self._set_combo_items(
            self.program_filter,
            sorted(
                ((name, program_id) for program_id, name in programs.items()),
                key=lambda item: item[0].casefold(),
            ),
        )

    def refresh_tasks(self):
        try:
            self._tasks = list_active_tasks()
            self._tasks_by_id = {
                task["zadanie_id"]: task for task in self._tasks
            }
            self._patients = {}
            oracle_error = None
            for task in self._tasks:
                patient_key = str(task["pacjent_id"])
                if patient_key in self._patients:
                    continue
                if oracle_error is not None:
                    self._patients[patient_key] = None
                    continue
                try:
                    self._patients[patient_key] = get_patient(
                        task["pacjent_id"]
                    )
                except Exception as exc:
                    oracle_error = exc
                    self._patients[patient_key] = None
            self._refresh_filters()
            self.apply_filters()
            if oracle_error:
                self.info_label.setText(
                    "Dane pacjentów z Oracle są niedostępne. "
                    "Wyświetlono identyfikatory."
                )
            else:
                self.info_label.setText(
                    f"Aktywne zadania: {len(self._tasks)}"
                )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się pobrać zadań:\n\n{exc}",
            )

    def apply_filters(self):
        status = self.status_filter.currentData()
        coordinator = self.coordinator_filter.currentData()
        program_id = self.program_filter.currentData()
        visible = [
            task
            for task in self._tasks
            if (status is None or str(task["status"] or "") == status)
            and (
                coordinator is None
                or str(task["koordynator_id"] or "") == coordinator
            )
            and (program_id is None or task["program_id"] == program_id)
        ]

        self.table.setRowCount(len(visible))
        for row_index, task in enumerate(visible):
            patient = self._patients.get(str(task["pacjent_id"]))
            values = [
                _patient_name(patient, task["pacjent_id"]),
                task["nazwa_w_sciezce"] or task["klocek_nazwa"] or "",
                task["status"] or "",
                task["data_zaplanowana"] or task["data_wymagana_do"] or "",
                task["program_nazwa"] or task["program_kod"] or "",
                task["sciezka_nazwa"] or task["sciezka_kod"] or "",
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column_index == 0:
                    item.setData(
                        Qt.ItemDataRole.UserRole,
                        task["zadanie_id"],
                    )
                self.table.setItem(row_index, column_index, item)

    def selected_task_id(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _selected_task(self):
        task_id = self.selected_task_id()
        if task_id is None:
            QMessageBox.information(
                self,
                "KOMPAS",
                "Wybierz zadanie.",
            )
            return None
        return self._tasks_by_id.get(task_id)

    def schedule_selected_task(self):
        task = self._selected_task()
        if task is None:
            return
        dialog = ScheduleTaskDialog(task["data_zaplanowana"], self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            schedule_task(task["zadanie_id"], dialog.planned_at())
            self.refresh_tasks()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się zaplanować zadania:\n\n{exc}",
            )

    def complete_selected_task(self):
        task = self._selected_task()
        if task is None:
            return
        answer = QMessageBox.question(
            self,
            "KOMPAS",
            "Oznaczyć wybrane zadanie jako zrealizowane?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            activated = complete_task(task["zadanie_id"])
            self.refresh_tasks()
            QMessageBox.information(
                self,
                "KOMPAS",
                "Zadanie oznaczono jako zrealizowane.\n"
                f"Nowe aktywne zadania: {len(activated)}.",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się zakończyć zadania:\n\n{exc}",
            )

    def cancel_selected_task(self):
        task = self._selected_task()
        if task is None:
            return
        answer = QMessageBox.question(
            self,
            "KOMPAS",
            "Anulować wybrane zadanie?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            cancel_task(task["zadanie_id"])
            self.refresh_tasks()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się anulować zadania:\n\n{exc}",
            )
