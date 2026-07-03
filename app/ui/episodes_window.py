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
    QVBoxLayout,
    QWidget,
)

from app.repositories.episode_repository import (
    get_episode,
    list_active_episodes,
)
from app.repositories.patient_repository import get_patient
from pathway_service import list_episode_tasks


def _display_name(patient, fallback):
    if patient:
        name = " ".join(
            part
            for part in (
                patient.get("nazwisko"),
                patient.get("imie"),
            )
            if part
        ).strip()
        if name:
            return name
    return str(fallback)


class EpisodeDetailsDialog(QDialog):
    def __init__(self, epizod_id, patient=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("KOMPAS — Szczegóły epizodu")
        self.resize(850, 560)

        episode = get_episode(epizod_id)
        if episode is None:
            raise ValueError(f"Nie znaleziono epizodu o ID {epizod_id}")

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow(
            "Pacjent:",
            QLabel(_display_name(patient, episode["pacjent_id"])),
        )
        form.addRow(
            "PESEL:",
            QLabel(str(patient.get("pesel") or "") if patient else ""),
        )
        form.addRow(
            "Program:",
            QLabel(episode["program_nazwa"] or episode["program_kod"] or ""),
        )
        form.addRow(
            "Ścieżka:",
            QLabel(episode["sciezka_nazwa"] or episode["sciezka_kod"] or ""),
        )
        form.addRow(
            "Koordynator:",
            QLabel(str(episode["koordynator_id"] or "Nie przypisano")),
        )
        form.addRow("Status:", QLabel(str(episode["status"] or "")))
        form.addRow(
            "Data rozpoczęcia:",
            QLabel(str(episode["data_start"] or "")),
        )
        form.addRow("Uwagi:", QLabel(str(episode["uwagi"] or "")))
        layout.addLayout(form)

        layout.addWidget(QLabel("Zadania epizodu"))
        tasks = list_episode_tasks(epizod_id)
        self.tasks_table = QTableWidget(len(tasks), 5)
        self.tasks_table.setHorizontalHeaderLabels(
            ["Lp", "Zadanie", "Status", "Zaplanowano", "Zrealizowano"]
        )
        self.tasks_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.tasks_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.tasks_table.verticalHeader().setVisible(False)
        self.tasks_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.tasks_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        for row_index, task in enumerate(tasks):
            values = [
                task["lp"],
                task["nazwa_w_sciezce"] or task["klocek_nazwa"],
                task["status"],
                task["data_zaplanowana"],
                task["data_realizacji"],
            ]
            for column_index, value in enumerate(values):
                self.tasks_table.setItem(
                    row_index,
                    column_index,
                    QTableWidgetItem("" if value is None else str(value)),
                )
        layout.addWidget(self.tasks_table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class EpisodesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KOMPAS — Aktywne epizody")
        self.resize(1200, 680)
        self._episodes = []
        self._patients = {}

        layout = QVBoxLayout(self)
        title = QLabel("Aktywne epizody")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        filters = QHBoxLayout()
        self.program_filter = QComboBox()
        self.coordinator_filter = QComboBox()
        self.status_filter = QComboBox()
        self.refresh_button = QPushButton("Odśwież")
        filters.addWidget(QLabel("Program:"))
        filters.addWidget(self.program_filter, 1)
        filters.addWidget(QLabel("Koordynator:"))
        filters.addWidget(self.coordinator_filter, 1)
        filters.addWidget(QLabel("Status:"))
        filters.addWidget(self.status_filter, 1)
        filters.addWidget(self.refresh_button)
        layout.addLayout(filters)

        self.info_label = QLabel()
        layout.addWidget(self.info_label)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [
                "Pacjent",
                "PESEL",
                "Program",
                "Ścieżka",
                "Koordynator",
                "Status",
                "Data rozpoczęcia",
            ]
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
            0, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table, 1)

        self.refresh_button.clicked.connect(self.refresh_episodes)
        self.program_filter.currentIndexChanged.connect(self.apply_filters)
        self.coordinator_filter.currentIndexChanged.connect(self.apply_filters)
        self.status_filter.currentIndexChanged.connect(self.apply_filters)
        self.table.cellDoubleClicked.connect(self.open_episode_details)

        self.refresh_episodes()

    def _load_patient(self, patient_id):
        key = str(patient_id)
        if key not in self._patients:
            self._patients[key] = get_patient(patient_id)
        return self._patients[key]

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
        programs = {}
        coordinators = set()
        statuses = set()
        for episode in self._episodes:
            if episode["program_id"] is not None:
                programs[episode["program_id"]] = (
                    episode["program_nazwa"]
                    or episode["program_kod"]
                    or str(episode["program_id"])
                )
            coordinators.add(str(episode["koordynator_id"] or ""))
            statuses.add(str(episode["status"] or ""))

        self._set_combo_items(
            self.program_filter,
            sorted(
                ((name, program_id) for program_id, name in programs.items()),
                key=lambda item: item[0].casefold(),
            ),
        )
        self._set_combo_items(
            self.coordinator_filter,
            [
                (value or "Nie przypisano", value)
                for value in sorted(coordinators, key=str.casefold)
            ],
        )
        self._set_combo_items(
            self.status_filter,
            [(value or "Brak statusu", value) for value in sorted(statuses)],
        )

    def refresh_episodes(self):
        try:
            self._episodes = list_active_episodes()
            self._patients = {}
            oracle_error = None
            for episode in self._episodes:
                try:
                    self._load_patient(episode["pacjent_id"])
                except Exception as exc:
                    oracle_error = exc
                    self._patients[str(episode["pacjent_id"])] = None
            self._refresh_filters()
            self.apply_filters()
            if oracle_error:
                self.info_label.setText(
                    "Nie udało się pobrać części danych pacjentów z Oracle. "
                    "Wyświetlono identyfikatory pacjentów."
                )
            else:
                self.info_label.setText(
                    f"Aktywne epizody: {len(self._episodes)}"
                )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się pobrać epizodów:\n\n{exc}",
            )

    def apply_filters(self):
        program_id = self.program_filter.currentData()
        coordinator = self.coordinator_filter.currentData()
        status = self.status_filter.currentData()
        visible = [
            episode
            for episode in self._episodes
            if (program_id is None or episode["program_id"] == program_id)
            and (
                coordinator is None
                or str(episode["koordynator_id"] or "") == coordinator
            )
            and (status is None or str(episode["status"] or "") == status)
        ]

        self.table.setRowCount(len(visible))
        for row_index, episode in enumerate(visible):
            patient = self._patients.get(str(episode["pacjent_id"]))
            values = [
                _display_name(patient, episode["pacjent_id"]),
                patient.get("pesel") if patient else "",
                episode["program_nazwa"] or episode["program_kod"] or "",
                episode["sciezka_nazwa"] or episode["sciezka_kod"] or "",
                episode["koordynator_id"] or "Nie przypisano",
                episode["status"] or "",
                episode["data_start"] or "",
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column_index == 0:
                    item.setData(
                        Qt.ItemDataRole.UserRole,
                        episode["epizod_id"],
                    )
                self.table.setItem(row_index, column_index, item)

    def open_episode_details(self, row, _column):
        item = self.table.item(row, 0)
        epizod_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        if epizod_id is None:
            return
        try:
            episode = get_episode(epizod_id)
            patient = (
                self._patients.get(str(episode["pacjent_id"]))
                if episode
                else None
            )
            dialog = EpisodeDetailsDialog(epizod_id, patient, self)
            dialog.exec()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się otworzyć szczegółów epizodu:\n\n{exc}",
            )
