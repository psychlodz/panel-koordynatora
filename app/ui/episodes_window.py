from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
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

from app.gateway.eskulap_gateway import EskulapGateway
from app.repositories.episode_repository import (
    get_episode,
    list_episodes,
)
from app.ui.episode_details_window import EpisodeDetailsDialog
from app.ui.widgets.busy_indicator import busy_operation
from app.ui.ui_helpers import create_help_button


CONTACT_TOOLTIP = (
    "Dane kontaktowe są pobierane z Eskulapa i nie są zapisywane w KOMPAS."
)


def _patient_value(patient, field_name):
    if patient is None:
        return None
    if isinstance(patient, dict):
        return patient.get(field_name)
    return getattr(patient, field_name, None)


def _contact_value(patient, primary_field, guardian_field):
    return (
        _patient_value(patient, primary_field)
        or _patient_value(patient, guardian_field)
        or "brak"
    )


class EpisodesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KOMPAS — Pacjenci w programach")
        self.resize(1500, 720)
        self._episodes = []
        self._patients = {}

        layout = QVBoxLayout(self)
        title = QLabel("Pacjenci w programach")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        filters = QHBoxLayout()
        self.program_filter = QComboBox()
        self.coordinator_filter = QComboBox()
        self.status_filter = QComboBox()
        self.refresh_button = QPushButton("Odśwież")
        self.help_button = create_help_button(
            self,
            "Pacjenci w programach",
            "To okno pokazuje epizody pacjentów i postęp realizacji "
            "programów.\n\n"
            "Możesz filtrować listę, odświeżyć dane i otworzyć szczegóły "
            "epizodu dwukrotnym kliknięciem.\n\n"
            "Nie edytuj danych pacjenta w tym widoku — pochodzą one z "
            "Eskulapa.",
        )
        self.refresh_button.setToolTip("Pobierz ponownie listę epizodów.")
        filters.addWidget(QLabel("Program:"))
        filters.addWidget(self.program_filter, 1)
        filters.addWidget(QLabel("Koordynator:"))
        filters.addWidget(self.coordinator_filter, 1)
        filters.addWidget(QLabel("Status:"))
        filters.addWidget(self.status_filter, 1)
        filters.addWidget(self.refresh_button)
        filters.addWidget(self.help_button)
        layout.addLayout(filters)

        self.info_label = QLabel()
        layout.addWidget(self.info_label)

        self.table = QTableWidget(0, 13)
        self.table.setHorizontalHeaderLabels(
            [
                "ID",
                "ID pacjenta",
                "Telefon",
                "E-mail",
                "Program",
                "Ścieżka",
                "Status",
                "Data rozpoczęcia",
                "Data zakończenia",
                "Koordynator",
                "Zadania",
                "Zrealizowane",
                "Realizacja",
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
            4, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeaderItem(2).setToolTip(CONTACT_TOOLTIP)
        self.table.horizontalHeaderItem(3).setToolTip(CONTACT_TOOLTIP)
        layout.addWidget(self.table, 1)

        self.refresh_button.clicked.connect(self.refresh_episodes)
        self.program_filter.currentIndexChanged.connect(self.apply_filters)
        self.coordinator_filter.currentIndexChanged.connect(self.apply_filters)
        self.status_filter.currentIndexChanged.connect(self.apply_filters)
        self.table.cellDoubleClicked.connect(self.open_episode_details)

        self.refresh_episodes()

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
            with busy_operation(
                self,
                "Trwa pobieranie epizodów i danych kontaktowych...",
            ):
                self._episodes = list_episodes()
                self._patients = {}
                gateway = EskulapGateway()
                oracle_error = None
                for episode in self._episodes:
                    patient_id = str(episode["pacjent_id"])
                    if patient_id in self._patients:
                        continue
                    if oracle_error is not None:
                        self._patients[patient_id] = None
                        continue
                    try:
                        self._patients[patient_id] = gateway.get_patient(
                            patient_id
                        )
                    except Exception as exc:
                        oracle_error = exc
                        self._patients[patient_id] = None
            self._refresh_filters()
            self.apply_filters()
            info = f"Epizody: {len(self._episodes)}"
            if oracle_error is not None:
                info += (
                    " — dane kontaktowe z Eskulapa są obecnie niedostępne"
                )
                self.info_label.setToolTip(str(oracle_error))
            else:
                self.info_label.setToolTip(CONTACT_TOOLTIP)
            self.info_label.setText(info)
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
                episode["epizod_id"],
                episode["pacjent_id"],
                _contact_value(
                    patient,
                    "phone",
                    "guardian_phone",
                ),
                _contact_value(
                    patient,
                    "email",
                    "guardian_email",
                ),
                episode["program_nazwa"] or episode["program_kod"] or "",
                episode["sciezka_nazwa"] or episode["sciezka_kod"] or "",
                episode["status"] or "",
                episode["data_start"] or "",
                episode["data_zakonczenia"] or "",
                episode["koordynator_id"] or "Nie przypisano",
                episode["liczba_zadan"],
                episode["liczba_zrealizowanych_zadan"],
                f"{episode['procent_realizacji']:.1f}%",
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column_index == 0:
                    item.setData(
                        Qt.ItemDataRole.UserRole,
                        episode["epizod_id"],
                    )
                if column_index in (2, 3):
                    item.setToolTip(CONTACT_TOOLTIP)
                self.table.setItem(row_index, column_index, item)

    def open_episode_details(self, row, _column):
        item = self.table.item(row, 0)
        epizod_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        if epizod_id is None:
            return
        try:
            with busy_operation(
                self,
                "Trwa pobieranie szczegółów epizodu z Oracle...",
            ):
                episode = get_episode(epizod_id)
                if episode is None:
                    raise ValueError("Wybrany epizod nie istnieje")
                patient = self._patients.get(
                    str(episode["pacjent_id"])
                )
                dialog = EpisodeDetailsDialog(
                    epizod_id,
                    patient=patient,
                    parent=self,
                )
            dialog.exec()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się otworzyć szczegółów epizodu:\n\n{exc}",
            )
