from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.gateway.eskulap_gateway import EskulapGateway
from app.repositories.episode_dashboard_repository import (
    FILTER_ACTIVE,
    FILTER_COMPLETED_MONTH,
    FILTER_OVERDUE,
    FILTER_SCHEDULED_TODAY,
    FILTER_TO_PLAN,
    FILTER_WAITING_ESKULAP,
    get_dashboard_summary,
    list_dashboard_episodes,
)
from app.services.work_context import work_context
from app.ui.episode_details_window import EpisodeDetailsDialog
from app.ui.theme.process_colors import task_status_colors
from app.ui.ui_helpers import create_help_button
from app.ui.widgets.busy_indicator import busy_operation


CONTACT_TOOLTIP = (
    "Dane kontaktowe są pobierane z Eskulapa i nie są zapisywane w KOMPAS."
)
HELP_TEXT = (
    "Dashboard epizodów pokazuje pacjentów realizujących programy, "
    "najbliższe zadania oraz elementy wymagające uwagi koordynatora."
)


def _patient_value(patient, field_name):
    return getattr(patient, field_name, None) if patient is not None else None


def _patient_name(patient, patient_id):
    name = " ".join(
        value
        for value in (
            _patient_value(patient, "last_name"),
            _patient_value(patient, "first_name"),
        )
        if value
    ).strip()
    return name or str(patient_id)


def _contact_value(patient, primary_field, guardian_field):
    return (
        _patient_value(patient, primary_field)
        or _patient_value(patient, guardian_field)
        or "brak"
    )


class SummaryTile(QPushButton):
    def __init__(self, title, status_role="info", parent=None):
        super().__init__(parent)
        self.title = title
        self.setObjectName("summaryTile")
        self.setProperty("statusRole", status_role)
        self.setCheckable(True)
        self.setMinimumHeight(96)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_value(0)

    def set_value(self, value):
        self.setText(f"{int(value)}\n{self.title}")


class EpisodesDashboardWindow(QWidget):
    def __init__(self, current_user=None, current_unit=None):
        super().__init__()
        self.current_user = (
            current_user
            if current_user is not None
            else work_context.current_user
        )
        self.initial_unit = (
            current_unit
            if current_unit is not None
            else work_context.current_unit
        )
        self._episodes = []
        self._patients = {}
        self._quick_filter = None
        self._initial_unit_selected = False
        self._oracle_error = None

        self.setWindowTitle("KOMPAS — Dashboard epizodów")
        self.resize(1680, 900)

        layout = QVBoxLayout(self)
        title = QLabel("Dashboard epizodów")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        summary_layout = QGridLayout()
        summary_layout.setHorizontalSpacing(12)
        summary_layout.setVerticalSpacing(12)
        tile_definitions = (
            (
                FILTER_ACTIVE,
                "Aktywne epizody",
                "active_episodes",
                "active",
            ),
            (
                FILTER_TO_PLAN,
                "Do zaplanowania",
                "episodes_to_plan",
                "toPlan",
            ),
            (
                FILTER_OVERDUE,
                "Po terminie",
                "overdue_episodes",
                "overdue",
            ),
            (
                FILTER_SCHEDULED_TODAY,
                "Zadania na dziś",
                "tasks_scheduled_today",
                "today",
            ),
            (
                FILTER_WAITING_ESKULAP,
                "Oczekujące na Eskulap",
                "waiting_for_eskulap",
                "waiting",
            ),
            (
                FILTER_COMPLETED_MONTH,
                "Zakończone w miesiącu",
                "completed_this_month",
                "completedMonth",
            ),
        )
        self.summary_tiles = {}
        self.summary_keys = {}
        for index, (
            filter_key,
            label,
            summary_key,
            status_role,
        ) in enumerate(
            tile_definitions
        ):
            tile = SummaryTile(label, status_role)
            tile.setToolTip(
                f"Pokaż w tabeli: {label.lower()}."
            )
            tile.clicked.connect(
                lambda _checked=False, key=filter_key: (
                    self.set_quick_filter(key)
                )
            )
            summary_layout.addWidget(tile, index // 3, index % 3)
            summary_layout.setColumnStretch(index % 3, 1)
            self.summary_tiles[filter_key] = tile
            self.summary_keys[filter_key] = summary_key
        layout.addLayout(summary_layout)

        filters = QHBoxLayout()
        self.program_filter = QComboBox()
        self.status_filter = QComboBox()
        self.coordinator_filter = QComboBox()
        self.unit_filter = QComboBox()
        for label, combo in (
            ("Program:", self.program_filter),
            ("Status:", self.status_filter),
            ("Koordynator:", self.coordinator_filter),
            ("Jednostka:", self.unit_filter),
        ):
            filters.addWidget(QLabel(label))
            filters.addWidget(combo, 1)

        self.refresh_button = QPushButton("Odśwież")
        self.refresh_button.setToolTip(
            "Pobierz ponownie epizody i aktualne dane pacjentów."
        )
        filters.addWidget(self.refresh_button)
        layout.addLayout(filters)

        self.info_label = QLabel()
        layout.addWidget(self.info_label)

        self.table = QTableWidget(0, 12)
        self.table.setHorizontalHeaderLabels(
            [
                "Pacjent",
                "Telefon",
                "E-mail",
                "Program",
                "Ścieżka",
                "Status epizodu",
                "Realizacja",
                "Najbliższe zadanie",
                "Termin",
                "Status zadania",
                "Koordynator",
                "Jednostka",
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
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(54)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        for column in (0, 7):
            self.table.horizontalHeader().setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.Stretch,
            )
        self.table.horizontalHeaderItem(1).setToolTip(CONTACT_TOOLTIP)
        self.table.horizontalHeaderItem(2).setToolTip(CONTACT_TOOLTIP)
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        self.details_button = QPushButton("Szczegóły epizodu")
        self.details_button.setToolTip(
            "Otwórz szczegóły zaznaczonego epizodu."
        )
        self.help_button = create_help_button(
            self,
            "Dashboard epizodów",
            HELP_TEXT,
        )
        self.close_button = QPushButton("Zamknij")
        self.close_button.setToolTip("Zamknij dashboard epizodów.")
        actions.addWidget(self.details_button)
        actions.addWidget(self.help_button)
        actions.addStretch(1)
        actions.addWidget(self.close_button)
        layout.addLayout(actions)

        self.refresh_button.clicked.connect(self.refresh_dashboard)
        self.details_button.clicked.connect(self.open_selected_episode)
        self.close_button.clicked.connect(self.close)
        self.table.cellDoubleClicked.connect(
            lambda _row, _column: self.open_selected_episode()
        )
        for combo in (
            self.program_filter,
            self.status_filter,
            self.coordinator_filter,
            self.unit_filter,
        ):
            combo.currentIndexChanged.connect(self.apply_filters)

        self.refresh_dashboard()

    @staticmethod
    def _set_combo_items(combo, items):
        selected = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Wszystkie", None)
        for text, value in items:
            combo.addItem(text, value)
        selected_index = combo.findData(selected)
        combo.setCurrentIndex(
            selected_index if selected_index >= 0 else 0
        )
        combo.blockSignals(False)

    def _refresh_filter_options(self):
        programs = {}
        statuses = set()
        coordinators = set()
        units = {}
        for episode in self._episodes:
            if episode["program_id"] is not None:
                programs[episode["program_id"]] = (
                    episode["program_nazwa"]
                    or episode["program_kod"]
                    or str(episode["program_id"])
                )
            statuses.add(str(episode["status"] or ""))
            coordinators.add(str(episode["koordynator_id"] or ""))
            for unit_id, symbol, name in zip(
                episode["unit_ids"],
                episode["unit_symbols"],
                episode["unit_names"],
            ):
                units[unit_id] = (
                    f"{symbol} - {name}" if name != symbol else symbol
                )

        self._set_combo_items(
            self.program_filter,
            sorted(
                (
                    (name, program_id)
                    for program_id, name in programs.items()
                ),
                key=lambda item: item[0].casefold(),
            ),
        )
        self._set_combo_items(
            self.status_filter,
            [
                (status or "Brak statusu", status)
                for status in sorted(statuses, key=str.casefold)
            ],
        )
        self._set_combo_items(
            self.coordinator_filter,
            [
                (
                    coordinator or "Nie przypisano",
                    coordinator,
                )
                for coordinator in sorted(
                    coordinators,
                    key=str.casefold,
                )
            ],
        )
        self._set_combo_items(
            self.unit_filter,
            sorted(
                (
                    (display_name, unit_id)
                    for unit_id, display_name in units.items()
                ),
                key=lambda item: item[0].casefold(),
            ),
        )
        if not self._initial_unit_selected and self.initial_unit is not None:
            unit_id = str(self.initial_unit.jo_id)
            index = self.unit_filter.findData(unit_id)
            if index >= 0:
                self.unit_filter.setCurrentIndex(index)
            self._initial_unit_selected = True

    def _load_patients(self):
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
        return oracle_error

    def refresh_dashboard(self):
        try:
            with busy_operation(
                self,
                "Trwa pobieranie dashboardu i danych pacjentów...",
            ):
                summary = get_dashboard_summary(
                    current_user=self.current_user,
                )
                self._episodes = list_dashboard_episodes(
                    current_user=self.current_user,
                )
                self._oracle_error = self._load_patients()
            for filter_key, tile in self.summary_tiles.items():
                tile.set_value(summary[self.summary_keys[filter_key]])
            self._refresh_filter_options()
            self.apply_filters()
            if self._oracle_error is not None:
                self.info_label.setToolTip(str(self._oracle_error))
            else:
                self.info_label.setToolTip(CONTACT_TOOLTIP)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się pobrać dashboardu:\n\n{exc}",
            )

    def set_quick_filter(self, filter_key):
        self._quick_filter = (
            None if self._quick_filter == filter_key else filter_key
        )
        for key, tile in self.summary_tiles.items():
            tile.setChecked(key == self._quick_filter)
        self.apply_filters()

    @staticmethod
    def _matches_quick_filter(episode, quick_filter):
        fields = {
            FILTER_ACTIVE: "is_active",
            FILTER_TO_PLAN: "has_to_plan",
            FILTER_OVERDUE: "has_overdue",
            FILTER_SCHEDULED_TODAY: "has_scheduled_today",
            FILTER_WAITING_ESKULAP: "waiting_for_eskulap",
            FILTER_COMPLETED_MONTH: "completed_this_month",
        }
        field = fields.get(quick_filter)
        return field is None or bool(episode[field])

    def apply_filters(self):
        program_id = self.program_filter.currentData()
        status = self.status_filter.currentData()
        coordinator = self.coordinator_filter.currentData()
        unit_id = self.unit_filter.currentData()
        visible = [
            episode
            for episode in self._episodes
            if (
                program_id is None
                or episode["program_id"] == program_id
            )
            and (
                status is None
                or str(episode["status"] or "") == status
            )
            and (
                coordinator is None
                or str(episode["koordynator_id"] or "")
                == coordinator
            )
            and (
                unit_id is None
                or unit_id in episode["unit_ids"]
            )
            and self._matches_quick_filter(
                episode,
                self._quick_filter,
            )
        ]

        self.table.setRowCount(len(visible))
        for row_index, episode in enumerate(visible):
            patient = self._patients.get(str(episode["pacjent_id"]))
            values = (
                _patient_name(patient, episode["pacjent_id"]),
                _contact_value(patient, "phone", "guardian_phone"),
                _contact_value(patient, "email", "guardian_email"),
                episode["program_nazwa"] or episode["program_kod"] or "",
                episode["sciezka_nazwa"] or episode["sciezka_kod"] or "",
                episode["status"] or "",
                f"{episode['procent_realizacji']:.1f}%",
                episode["next_task_name"] or "brak",
                episode["next_task_due"] or "brak",
                episode["next_task_status"] or "brak",
                episode["koordynator_id"] or "Nie przypisano",
                ", ".join(episode["unit_symbols"]) or "Nie przypisano",
            )
            for column_index, value in enumerate(values):
                if column_index == 6:
                    progress = QProgressBar()
                    progress.setRange(0, 100)
                    progress_value = int(
                        round(episode["procent_realizacji"])
                    )
                    progress.setValue(progress_value)
                    progress.setFormat(f"{progress_value}%")
                    progress.setProperty(
                        "statusRole",
                        (
                            "success"
                            if progress_value >= 100
                            else "info"
                            if progress_value > 0
                            else "warning"
                        ),
                    )
                    self.table.setCellWidget(
                        row_index,
                        column_index,
                        progress,
                    )
                    continue
                item = QTableWidgetItem(str(value))
                if column_index == 0:
                    item.setData(
                        Qt.ItemDataRole.UserRole,
                        episode["epizod_id"],
                    )
                if column_index in (6, 8, 9):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignLeft
                        | Qt.AlignmentFlag.AlignVCenter
                    )
                    item.setToolTip(str(value))
                if column_index in (1, 2):
                    item.setToolTip(CONTACT_TOOLTIP)
                if column_index == 7:
                    background = QColor(
                        str(episode.get("next_task_color") or "")
                    )
                    foreground = QColor(
                        str(episode.get("next_task_text_color") or "")
                    )
                    if background.isValid():
                        item.setBackground(background)
                    if foreground.isValid():
                        item.setForeground(foreground)
                if column_index in (8, 9):
                    colors = task_status_colors(
                        episode["next_task_status"],
                        overdue=bool(episode["has_overdue"]),
                    )
                    if colors:
                        item.setBackground(QColor(colors[0]))
                        item.setForeground(QColor(colors[1]))
                self.table.setItem(row_index, column_index, item)

        info = (
            f"Widoczne epizody: {len(visible)} z {len(self._episodes)}"
        )
        if self._oracle_error is not None:
            info += (
                " — brak danych pacjentów z Eskulapa; "
                "wyświetlono identyfikatory"
            )
        self.info_label.setText(info)

    def selected_episode_id(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return (
            item.data(Qt.ItemDataRole.UserRole)
            if item is not None
            else None
        )

    def open_selected_episode(self):
        epizod_id = self.selected_episode_id()
        if epizod_id is None:
            QMessageBox.information(
                self,
                "KOMPAS",
                "Wybierz epizod, aby otworzyć jego szczegóły.",
            )
            return
        patient = next(
            (
                self._patients.get(str(episode["pacjent_id"]))
                for episode in self._episodes
                if episode["epizod_id"] == epizod_id
            ),
            None,
        )
        try:
            with busy_operation(
                self,
                "Trwa pobieranie szczegółów epizodu...",
            ):
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
                "Nie udało się otworzyć szczegółów epizodu:\n\n"
                f"{exc}",
            )


# Zgodność z dotychczasowymi importami modułu epizodów.
EpisodesWindow = EpisodesDashboardWindow
