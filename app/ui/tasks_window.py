from PySide6.QtCore import QDate, QTimer, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenuBar,
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
from app.ui.widgets.busy_indicator import busy_operation
from episode_generator import complete_task
from services.synchronization_service import synchronize_tasks


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


class TasksWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KOMPAS — Aktywne zadania")
        self.resize(1250, 680)
        self._tasks = []
        self._tasks_by_id = {}
        self._patients = {}
        self._scheduling_task_id = None
        self.schedule_window = None

        layout = QVBoxLayout(self)
        menu_bar = QMenuBar(self)
        administration_menu = menu_bar.addMenu("Administracja")
        self.synchronize_action = administration_menu.addAction(
            "Synchronizuj teraz"
        )
        layout.setMenuBar(menu_bar)

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
        self.synchronize_action.triggered.connect(self.synchronize_now)

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
            with busy_operation(
                self,
                "Trwa pobieranie zadań i danych pacjentów...",
            ):
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
        try:
            from plan_pracy import PlanPracyApp

            self._scheduling_task_id = task["zadanie_id"]
            self.schedule_window = PlanPracyApp(
                selection_mode=True,
                initial_notes=task["uwagi"],
            )
            self.schedule_window.slot_selected.connect(
                self.save_selected_schedule_slot
            )
            if task["data_zaplanowana"]:
                planned_date = QDate.fromString(
                    str(task["data_zaplanowana"])[:10],
                    Qt.DateFormat.ISODate,
                )
                if planned_date.isValid():
                    self.schedule_window.data_od.setDate(planned_date)
            self.schedule_window.show()
            QTimer.singleShot(0, self.schedule_window.zaladuj)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się otworzyć harmonogramu:\n\n{exc}",
            )

    def save_selected_schedule_slot(self, planned_at, notes):
        if self._scheduling_task_id is None:
            return
        try:
            schedule_task(
                self._scheduling_task_id,
                planned_at,
                notes,
            )
            if self.schedule_window is not None:
                self.schedule_window.close()
            self._scheduling_task_id = None
            self.schedule_window = None
            self.refresh_tasks()
            QMessageBox.information(
                self,
                "KOMPAS",
                "Zadanie zostało zaplanowane w Harmonogramie.",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się zapisać terminu zadania:\n\n{exc}",
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

    def synchronize_now(self):
        self.synchronize_action.setEnabled(False)
        self.info_label.setText("Synchronizacja z Eskulapem...")
        try:
            with busy_operation(
                self,
                "Trwa synchronizacja danych z Eskulapem...",
            ):
                result = synchronize_tasks()
            self.refresh_tasks()
            message = (
                f"Sprawdzeni pacjenci: {result.patients_checked}\n"
                f"Sprawdzone zadania: {result.tasks_checked}\n"
                f"Zrealizowane zadania: {result.tasks_completed}\n"
                f"Pominięte zadania: {result.tasks_skipped}"
            )
            if result.errors:
                message += f"\nBłędy: {len(result.errors)}"
            QMessageBox.information(
                self,
                "KOMPAS — Synchronizacja",
                message,
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS — Synchronizacja",
                f"Synchronizacja nie powiodła się:\n\n{exc}",
            )
        finally:
            self.synchronize_action.setEnabled(True)
