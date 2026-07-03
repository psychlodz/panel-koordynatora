from datetime import date, datetime

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHeaderView,
    QLabel,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from app.repositories.episode_repository import (
    get_episode,
    list_episode_tasks,
    list_episode_process_elements,
)
from app.repositories.event_repository import (
    get_patient_consultations,
    get_patient_imaging_orders,
    get_patient_laboratory_orders,
    get_patient_visits,
)
from app.repositories.patient_repository import get_patient


WAITING_STATUS = "OCZEKUJE NA AKTYWACJĘ"


def _text(value):
    return "" if value is None else str(value)


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


def _configure_table(table, stretch_column=1):
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setSectionResizeMode(
        QHeaderView.ResizeMode.ResizeToContents
    )
    table.horizontalHeader().setSectionResizeMode(
        stretch_column, QHeaderView.ResizeMode.Stretch
    )


def _event_date_key(event):
    value = event.event_date
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    return datetime.min


class EpisodeDetailsDialog(QDialog):
    def __init__(self, epizod_id, patient=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("KOMPAS — Szczegóły epizodu")
        self.resize(1400, 850)

        self.episode = get_episode(epizod_id)
        if self.episode is None:
            raise ValueError(f"Nie znaleziono epizodu o ID {epizod_id}")
        self.process_elements = list_episode_process_elements(epizod_id)
        self.tasks = list_episode_tasks(epizod_id)
        self.patient = patient
        self.oracle_errors = []

        if self.patient is None:
            try:
                self.patient = get_patient(self.episode["pacjent_id"])
            except Exception as exc:
                self.oracle_errors.append(f"Pacjent: {exc}")

        layout = QVBoxLayout(self)
        title = QLabel(f"Epizod #{epizod_id}")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.addWidget(self._patient_panel())
        top_splitter.addWidget(self._process_overview_panel())
        top_splitter.setStretchFactor(0, 1)
        top_splitter.setStretchFactor(1, 3)
        layout.addWidget(top_splitter, 2)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._process_tab(), "Proces")
        self._load_oracle_events()
        self.tabs.addTab(
            self._events_tab(self.consultations, "Brak konsultacji."),
            "Konsultacje",
        )
        self.tabs.addTab(
            self._events_tab(self.exams, "Brak badań."),
            "Badania",
        )
        self.tabs.addTab(
            self._events_tab(self.visits, "Brak wizyt."),
            "Wizyty",
        )
        self.tabs.addTab(
            self._events_tab(self.history, "Brak historii zdarzeń."),
            "Historia",
        )
        layout.addWidget(self.tabs, 3)

        if self.oracle_errors:
            warning = QLabel(
                "Nie udało się pobrać części danych Oracle. "
                "Dane procesu lokalnego pozostają dostępne."
            )
            warning.setStyleSheet("color: #a84300;")
            warning.setToolTip("\n".join(self.oracle_errors))
            layout.addWidget(warning)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _patient_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        heading = QLabel("Pacjent i program")
        heading.setStyleSheet("font-weight: bold;")
        layout.addWidget(heading)

        form = QFormLayout()
        form.addRow(
            "Pacjent:",
            QLabel(
                _patient_name(
                    self.patient,
                    self.episode["pacjent_id"],
                )
            ),
        )
        form.addRow(
            "PESEL:",
            QLabel(_text(self.patient.get("pesel")) if self.patient else ""),
        )
        form.addRow(
            "Program:",
            QLabel(
                _text(
                    self.episode["program_nazwa"]
                    or self.episode["program_kod"]
                )
            ),
        )
        form.addRow(
            "Ścieżka:",
            QLabel(
                _text(
                    self.episode["sciezka_nazwa"]
                    or self.episode["sciezka_kod"]
                )
            ),
        )
        form.addRow(
            "Koordynator:",
            QLabel(_text(self.episode["koordynator_id"] or "Nie przypisano")),
        )
        form.addRow("Status:", QLabel(_text(self.episode["status"])))
        form.addRow(
            "Data rozpoczęcia:",
            QLabel(_text(self.episode["data_start"])),
        )
        form.addRow(
            "Data zakończenia:",
            QLabel(_text(self.episode["data_zakonczenia"])),
        )
        form.addRow(
            "System źródłowy:",
            QLabel(_text(self.episode["source_system"])),
        )
        form.addRow(
            "Typ źródła:",
            QLabel(_text(self.episode["source_type"])),
        )
        form.addRow(
            "ID źródła:",
            QLabel(_text(self.episode["source_id"])),
        )
        form.addRow("Uwagi:", QLabel(_text(self.episode["uwagi"])))
        layout.addLayout(form)
        layout.addStretch(1)
        return panel

    def _process_overview_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        heading = QLabel("Elementy procesu")
        heading.setStyleSheet("font-weight: bold;")
        layout.addWidget(heading)

        table = QTableWidget(len(self.process_elements), 4)
        table.setHorizontalHeaderLabels(
            ["Element procesu", "Status", "Termin", "Realizacja"]
        )
        _configure_table(table, 0)
        for row_index, element in enumerate(self.process_elements):
            values = [
                element["nazwa_w_sciezce"] or element["klocek_nazwa"],
                element["status"] or WAITING_STATUS,
                element["data_wymagana_do"] or element["data_zaplanowana"],
                element["data_realizacji"],
            ]
            for column_index, value in enumerate(values):
                table.setItem(
                    row_index,
                    column_index,
                    QTableWidgetItem(_text(value)),
                )
        layout.addWidget(table)
        return panel

    def _process_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        table = QTableWidget(len(self.tasks), 7)
        table.setHorizontalHeaderLabels(
            [
                "Nazwa elementu",
                "Status",
                "Data wymagana do",
                "Zaplanowano",
                "Realizacja",
                "Źródło",
                "Uwagi",
            ]
        )
        _configure_table(table, 0)
        for row_index, task in enumerate(self.tasks):
            values = [
                task["nazwa_w_sciezce"] or task["klocek_nazwa"],
                task["status"],
                task["data_wymagana_do"],
                task["data_zaplanowana"],
                task["data_realizacji"],
                task["zrodlo"],
                task["uwagi"],
            ]
            for column_index, value in enumerate(values):
                table.setItem(
                    row_index,
                    column_index,
                    QTableWidgetItem(_text(value)),
                )
        layout.addWidget(table)
        return tab

    def _safe_events(self, label, loader):
        try:
            return loader(
                self.episode["pacjent_id"],
                self.episode["data_start"],
                self.episode["data_zakonczenia"],
            )
        except Exception as exc:
            self.oracle_errors.append(f"{label}: {exc}")
            return []

    def _load_oracle_events(self):
        self.consultations = self._safe_events(
            "Konsultacje",
            get_patient_consultations,
        )
        laboratory = self._safe_events(
            "Badania laboratoryjne",
            get_patient_laboratory_orders,
        )
        imaging = self._safe_events(
            "Badania obrazowe",
            get_patient_imaging_orders,
        )
        self.exams = laboratory + imaging
        self.exams.sort(key=_event_date_key, reverse=True)
        self.visits = self._safe_events("Wizyty", get_patient_visits)
        self.history = self.consultations + self.exams + self.visits
        self.history.sort(key=_event_date_key, reverse=True)

    @staticmethod
    def _events_tab(events, empty_message):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        if not events:
            label = QLabel(empty_message)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
            return tab

        table = QTableWidget(len(events), 6)
        table.setHorizontalHeaderLabels(
            ["Data", "Typ", "Status", "Planowana", "Opis", "Źródło"]
        )
        _configure_table(table, 4)
        for row_index, event in enumerate(events):
            values = [
                event.event_date,
                event.event_type,
                event.status,
                event.planned_date,
                event.description,
                event.source,
            ]
            for column_index, value in enumerate(values):
                table.setItem(
                    row_index,
                    column_index,
                    QTableWidgetItem(_text(value)),
                )
        layout.addWidget(table)
        return tab
