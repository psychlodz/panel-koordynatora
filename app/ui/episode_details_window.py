import logging
import re
import traceback
from datetime import date, datetime

from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QObject, QThread, Qt, Signal

from app.gateway.eskulap_gateway import EskulapGateway
from app.repositories.episode_repository import (
    get_episode,
    list_episode_tasks,
)
from app.ui.ui_helpers import create_help_button, polish_dialog_buttons
from app.services import episode_path_service
from app.services.debug_logging import (
    application_log_path,
    configure_application_logging,
)
from app.services.episode_synchronization_service import EpisodeSynchronizationService
from app.services.episode_state_service import EpisodeStateService
from app.services.work_context import work_context
from app.ui.episode_details_presenter import (
    WAITING_STATUS,
    eskulap_visit_details,
    eskulap_visit_tooltip,
    process_element_label,
    process_element_tooltip,
    status_with_date,
)
from app.ui.widgets.busy_indicator import hide_busy, show_busy


logger = logging.getLogger(__name__)

CONTACT_TOOLTIP = (
    "Dane kontaktowe są pobierane z Eskulapa i nie są zapisywane w KOMPAS."
)


class EpisodeRefreshWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, epizod_id):
        super().__init__()
        self.epizod_id = epizod_id

    def run(self):
        try:
            summary = EpisodeSynchronizationService().synchronize_episode(
                self.epizod_id
            )
            EpisodeStateService().calculate_episode_state(self.epizod_id)
            self.finished.emit(summary)
        except Exception:
            self.failed.emit(traceback.format_exc())


def _text(value):
    return "" if value is None else str(value)


def _date_part(value):
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()[:10]


def _time_part(value):
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value.strftime("%H:%M")
    text = str(value).strip()
    if len(text) >= 16 and re.match(r"\d{4}-\d{2}-\d{2}", text):
        return text[11:16]
    return text[:5]


def _is_plannable_element(element):
    block_code = str(element.get("klocek_kod") or "").strip().upper()
    source = str(element.get("eskulap_system") or "").strip().upper()
    return block_code in {
        "KONSULTACJA_SPECJALISTYCZNA",
        "BADANIE_OBRAZOWE",
    } or source in {
        "ESKULAP_KONSULTACJE",
        "ESKULAP_BADANIA_OBRAZOWE",
    }


def _validate_time(value, required=False):
    text = str(value or "").strip()
    if not text and not required:
        return None
    if not re.match(r"^\d{2}:\d{2}$", text):
        raise ValueError("Godzina musi mieć format HH:MM.")
    hour, minute = [int(part) for part in text.split(":")]
    if hour > 23 or minute > 59:
        raise ValueError("Podaj poprawną godzinę.")
    return text


def _patient_value(patient, field_name, legacy_name=None):
    if patient is None:
        return None
    if isinstance(patient, dict):
        return patient.get(field_name) or (
            patient.get(legacy_name) if legacy_name else None
        )
    return getattr(patient, field_name, None)


def _contact_text(patient, field_name):
    value = _patient_value(patient, field_name)
    return str(value).strip() if value else "brak"


def _patient_name(patient, fallback):
    if patient:
        name = " ".join(
            part
            for part in (
                _patient_value(patient, "last_name", "nazwisko"),
                _patient_value(patient, "first_name", "imie"),
            )
            if part
        ).strip()
        if name:
            return name
    return str(fallback)


def _configure_table(table, stretch_column=1):
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setAlternatingRowColors(True)
    table.setWordWrap(True)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(54)
    table.horizontalHeader().setSectionResizeMode(
        QHeaderView.ResizeMode.ResizeToContents
    )
    table.horizontalHeader().setSectionResizeMode(
        stretch_column, QHeaderView.ResizeMode.Stretch
    )
    table.horizontalHeader().setDefaultAlignment(
        Qt.AlignmentFlag.AlignCenter
    )


class EpisodeElementDuplicateDialog(QDialog):
    def __init__(self, element, parent=None):
        super().__init__(parent)
        self.setWindowTitle("KOMPAS — Powiel element procesu")
        self.resize(520, 420)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit(
            _text(element.get("nazwa_w_sciezce") or element.get("nazwa"))
        )
        self.lp_spin = QSpinBox()
        self.lp_spin.setRange(1, 999)
        self.lp_spin.setValue(int(element.get("lp") or 0) + 1)

        self.min_spin = QSpinBox()
        self.min_spin.setRange(0, 999)
        self.min_spin.setValue(1)

        self.max_spin = QSpinBox()
        self.max_spin.setRange(0, 999)
        self.max_spin.setSpecialValueText("brak")
        self.max_spin.setValue(1)

        self.term_spin = QSpinBox()
        self.term_spin.setRange(0, 999)
        self.term_spin.setSpecialValueText("brak")
        self.term_spin.setValue(
            int(element.get("termin_liczba") or 0)
        )

        self.required_check = QCheckBox("Wymagany")
        self.required_check.setChecked(bool(element.get("czy_wymagany", 1)))

        self.order_check = QCheckBox("Wymaga zlecenia lekarza")
        self.order_check.setChecked(
            bool(element.get("czy_wymaga_zlecenia", 0))
        )

        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText(
            "Np. konieczne dodatkowe wykonanie elementu"
        )

        form.addRow("Nazwa elementu:", self.name_edit)
        form.addRow("Pozycja w procesie:", self.lp_spin)
        form.addRow("Min.:", self.min_spin)
        form.addRow("Maks.:", self.max_spin)
        form.addRow("Termin liczba:", self.term_spin)
        form.addRow("", self.required_check)
        form.addRow("", self.order_check)
        form.addRow("Przyczyna:", self.reason_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        polish_dialog_buttons(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        reason = self.reason_edit.text().strip()
        return (
            {
                "nazwa": self.name_edit.text().strip(),
                "lp": self.lp_spin.value(),
                "min_liczba": self.min_spin.value(),
                "max_liczba": (
                    None if self.max_spin.value() == 0 else self.max_spin.value()
                ),
                "termin_liczba": (
                    None
                    if self.term_spin.value() == 0
                    else self.term_spin.value()
                ),
                "czy_wymagany": 1 if self.required_check.isChecked() else 0,
                "czy_wymaga_zlecenia": (
                    1 if self.order_check.isChecked() else 0
                ),
            },
            reason,
        )


class EpisodeElementPlanningDialog(QDialog):
    def __init__(self, element, parent=None):
        super().__init__(parent)
        self.element = element
        self.setWindowTitle("KOMPAS — Planowanie elementu epizodu")
        self.resize(620, 460)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        element_name = (
            element.get("nazwa_w_sciezce")
            or element.get("nazwa")
            or element.get("klocek_nazwa")
            or "Element procesu"
        )
        event_type = element.get("eskulap_system") or element.get("klocek_kod")
        source_name = element.get("eskulap_rodzaj_wizyty") or "brak"
        eskulap_planned = element.get("eskulap_plan_data")

        self.element_label = QLabel(_text(element_name))
        self.event_type_label = QLabel(_text(event_type))
        self.source_name_label = QLabel(_text(source_name))
        self.eskulap_plan_label = QLabel(
            _text(_date_part(eskulap_planned) or "brak")
            + (
                f" {_time_part(eskulap_planned)}"
                if _time_part(eskulap_planned)
                else ""
            )
        )

        local_plan = element.get("data_zaplanowana")
        default_source = local_plan or eskulap_planned
        self.date_edit = QLineEdit(_date_part(default_source) or date.today().isoformat())
        self.date_edit.setPlaceholderText("RRRR-MM-DD")
        self.time_from_edit = QLineEdit(_time_part(default_source) or "08:00")
        self.time_from_edit.setPlaceholderText("HH:MM")
        self.time_to_edit = QLineEdit(_time_part(element.get("kompas_plan_godz_do")))
        self.time_to_edit.setPlaceholderText("HH:MM, opcjonalnie")
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlainText(_text(element.get("kompas_plan_uwagi")))
        self.notes_edit.setPlaceholderText("Uwagi do terminu w KOMPAS, opcjonalnie")
        self.notes_edit.setMaximumHeight(90)

        form.addRow("Element:", self.element_label)
        form.addRow("Typ zdarzenia:", self.event_type_label)
        form.addRow("Nazwa z Eskulapa:", self.source_name_label)
        form.addRow("Data planowana w Eskulapie:", self.eskulap_plan_label)
        form.addRow("Data KOMPAS:", self.date_edit)
        form.addRow("Godzina od:", self.time_from_edit)
        form.addRow("Godzina do:", self.time_to_edit)
        form.addRow("Uwagi:", self.notes_edit)
        layout.addLayout(form)

        info = QLabel(
            "Status „Zaplanowana” zostanie ustawiony dopiero po zapisaniu "
            "terminu w KOMPAS. Data planowana z Eskulapa jest tylko informacją."
        )
        info.setWordWrap(True)
        info.setObjectName("infoLabel")
        layout.addWidget(info)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        polish_dialog_buttons(buttons)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _validate_and_accept(self):
        try:
            datetime.strptime(self.date_edit.text().strip(), "%Y-%m-%d")
            start = _validate_time(self.time_from_edit.text(), required=True)
            end = _validate_time(self.time_to_edit.text(), required=False)
            if end and end <= start:
                raise ValueError("Godzina zakończenia musi być późniejsza niż rozpoczęcia.")
        except ValueError as exc:
            QMessageBox.warning(self, "KOMPAS", str(exc))
            return
        self.accept()

    def values(self):
        return {
            "plan_date": self.date_edit.text().strip(),
            "time_from": self.time_from_edit.text().strip(),
            "time_to": self.time_to_edit.text().strip() or None,
            "notes": self.notes_edit.toPlainText().strip() or None,
        }


class EpisodeDetailsDialog(QDialog):
    def __init__(self, epizod_id, patient=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("KOMPAS — Szczegóły epizodu")
        self.resize(1400, 850)

        self.episode = get_episode(epizod_id)
        if self.episode is None:
            raise ValueError(f"Nie znaleziono epizodu o ID {epizod_id}")
        self.process_elements = EpisodeStateService().calculate_episode_state(
            epizod_id
        )["elements"]
        self.tasks = list_episode_tasks(epizod_id)
        self.patient = patient
        self.oracle_errors = []
        self.current_user = work_context.current_user
        self._process_overview_table = None
        self._refresh_thread = None
        self._refresh_worker = None
        self._refresh_selected_element_id = None

        if self.patient is None:
            try:
                self.patient = EskulapGateway().get_patient(
                    self.episode["pacjent_id"]
                )
            except Exception as exc:
                self.oracle_errors.append(f"Pacjent: {exc}")

        layout = QVBoxLayout(self)
        title = QLabel(f"Epizod #{epizod_id}")
        title.setObjectName("windowTitle")
        layout.addWidget(title)

        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.addWidget(self._patient_panel())
        top_splitter.addWidget(self._process_overview_panel())
        top_splitter.setStretchFactor(0, 1)
        top_splitter.setStretchFactor(1, 3)
        layout.addWidget(top_splitter, 2)

        if self.oracle_errors:
            warning = QLabel(
                "Nie udało się pobrać części danych Oracle. "
                "Dane procesu lokalnego pozostają dostępne."
            )
            warning.setObjectName("warningLabel")
            warning.setToolTip("\n".join(self.oracle_errors))
            layout.addWidget(warning)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        polish_dialog_buttons(buttons)
        close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        close_button.setToolTip("Zamknij szczegóły epizodu.")
        self.help_button = create_help_button(
            self,
            "Szczegóły epizodu",
            "To okno przedstawia dane epizodu oraz główną tabelę elementów "
            "procesu.\n\n"
            "Zaznacz element w tabeli, aby powielić, dezaktywować, "
            "reaktywować albo sprawdzić historię zmian. Przycisk Odśwież "
            "aktualizuje tylko bieżący epizod na podstawie danych z Eskulapa.\n\n"
            "Nie zmieniaj tutaj danych źródłowych Eskulapa ani wzorcowej "
            "ścieżki programu.",
        )
        buttons.addButton(
            self.help_button,
            QDialogButtonBox.ButtonRole.HelpRole,
        )
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _patient_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        heading = QLabel("Pacjent i program")
        heading.setObjectName("panelTitle")
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
            QLabel(
                _text(_patient_value(self.patient, "pesel"))
                if self.patient
                else ""
            ),
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

        contact_group = QGroupBox("Kontakt")
        contact_group.setToolTip(CONTACT_TOOLTIP)
        contact_form = QFormLayout(contact_group)
        contact_fields = (
            ("Telefon pacjenta:", "phone"),
            ("E-mail pacjenta:", "email"),
            ("Telefon opiekuna:", "guardian_phone"),
            ("E-mail opiekuna:", "guardian_email"),
        )
        for label, field_name in contact_fields:
            value_label = QLabel(
                _contact_text(self.patient, field_name)
            )
            value_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            value_label.setToolTip(CONTACT_TOOLTIP)
            contact_form.addRow(label, value_label)
        layout.addWidget(contact_group)
        layout.addStretch(1)
        return panel

    def _process_overview_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        heading = QLabel("Elementy procesu")
        heading.setObjectName("panelTitle")
        layout.addWidget(heading)

        actions = QHBoxLayout()
        self.btn_refresh_episode = QPushButton("Odśwież")
        self.btn_refresh_episode.setToolTip(
            "Pobierz aktualne dane z Eskulapa tylko dla tego epizodu."
        )
        self.btn_duplicate_element = QPushButton("Powiel element")
        self.btn_duplicate_element.setToolTip(
            "Utwórz dodatkowe wykonanie zaznaczonego elementu tylko w tym epizodzie."
        )
        self.btn_plan_element = QPushButton("Zaplanuj")
        self.btn_plan_element.setToolTip(
            "Zapisz albo zmień termin konsultacji lub badania obrazowego w KOMPAS."
        )
        self.btn_clear_plan_element = QPushButton("Usuń termin")
        self.btn_clear_plan_element.setToolTip(
            "Usuń lokalny termin KOMPAS dla zaznaczonego elementu."
        )
        self.btn_deactivate_element = QPushButton("Dezaktywuj element")
        self.btn_deactivate_element.setToolTip(
            "Wyłącz zaznaczony element w tym epizodzie bez usuwania go z historii."
        )
        self.btn_reactivate_element = QPushButton("Reaktywuj element")
        self.btn_reactivate_element.setToolTip(
            "Przywróć dezaktywowany element w tym epizodzie."
        )
        self.btn_history_element = QPushButton("Historia zmian")
        self.btn_history_element.setToolTip(
            "Pokaż historię zmian zaznaczonego elementu epizodu."
        )
        self.btn_refresh_episode.clicked.connect(self.refresh_from_eskulap)
        self.btn_duplicate_element.clicked.connect(self.duplicate_selected_element)
        self.btn_plan_element.clicked.connect(self.plan_selected_element)
        self.btn_clear_plan_element.clicked.connect(self.clear_selected_element_plan)
        self.btn_deactivate_element.clicked.connect(self.deactivate_selected_element)
        self.btn_reactivate_element.clicked.connect(self.reactivate_selected_element)
        self.btn_history_element.clicked.connect(self.show_selected_element_history)
        for button in (
            self.btn_refresh_episode,
            self.btn_duplicate_element,
            self.btn_plan_element,
            self.btn_clear_plan_element,
            self.btn_deactivate_element,
            self.btn_reactivate_element,
            self.btn_history_element,
        ):
            actions.addWidget(button)
        actions.addStretch(1)
        layout.addLayout(actions)

        table = QTableWidget(len(self.process_elements), 3)
        self._process_overview_table = table
        table.setHorizontalHeaderLabels(
            ["Element procesu", "Status", "Dane w Eskulap"]
        )
        _configure_table(table, 0)
        table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        table.itemSelectionChanged.connect(self.update_episode_path_buttons)
        self._populate_process_overview_table()
        layout.addWidget(table)
        self.update_episode_path_buttons()
        return panel

    def _populate_process_overview_table(self):
        table = self._process_overview_table
        if table is None:
            return
        table.setRowCount(len(self.process_elements))
        for row_index, element in enumerate(self.process_elements):
            values = [
                process_element_label(element),
                status_with_date(element),
                eskulap_visit_details(element),
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(_text(value))
                item.setData(
                    Qt.ItemDataRole.UserRole,
                    element.get("epizod_element_id"),
                )
                if column_index == 1:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignLeft
                        | Qt.AlignmentFlag.AlignVCenter
                    )
                    if column_index == 0:
                        item.setToolTip(process_element_tooltip(element))
                    else:
                        item.setToolTip(
                            eskulap_visit_tooltip(element)
                            if column_index == 2
                            else _text(value)
                        )
                table.setItem(
                    row_index,
                    column_index,
                    item,
                )
        table.resizeRowsToContents()

    def _selected_episode_element_id(self):
        table = self._process_overview_table
        if table is None:
            return None
        row = table.currentRow()
        if row < 0:
            return None
        item = table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.ItemDataRole.UserRole)
        if value is not None:
            return value
        return None

    def _selected_episode_element(self):
        element_id = self._selected_episode_element_id()
        if element_id is None:
            return None
        return next(
            (
                element
                for element in self.process_elements
                if element.get("epizod_element_id") == element_id
            ),
            None,
        )

    def update_episode_path_buttons(self):
        element = self._selected_episode_element()
        can_edit = episode_path_service.can_edit_episode_path(
            self.current_user
        )
        selected = element is not None
        for button in (
            self.btn_duplicate_element,
            self.btn_plan_element,
            self.btn_clear_plan_element,
            self.btn_deactivate_element,
            self.btn_reactivate_element,
            self.btn_history_element,
        ):
            button.setEnabled(selected and can_edit)
        self.btn_history_element.setEnabled(selected)
        if not can_edit:
            tooltip = "Operacja wymaga uprawnienia EPISODE_PATH_EDIT."
            self.btn_duplicate_element.setToolTip(tooltip)
            self.btn_plan_element.setToolTip(tooltip)
            self.btn_clear_plan_element.setToolTip(tooltip)
            self.btn_deactivate_element.setToolTip(tooltip)
            self.btn_reactivate_element.setToolTip(tooltip)
            return
        if element:
            is_active = bool(element.get("czy_aktywny", 1))
            self.btn_deactivate_element.setEnabled(is_active)
            self.btn_reactivate_element.setEnabled(not is_active)
            plannable = selected and is_active and _is_plannable_element(element)
            has_plan = bool(
                element.get("data_zaplanowana")
                or element.get("kompas_plan_data")
            )
            self.btn_plan_element.setEnabled(plannable)
            self.btn_plan_element.setText("Zmień termin" if has_plan else "Zaplanuj")
            self.btn_clear_plan_element.setEnabled(plannable and has_plan)
        else:
            self.btn_plan_element.setEnabled(False)
            self.btn_clear_plan_element.setEnabled(False)

    def _refresh_process(self, selected_element_id=None):
        if selected_element_id is None:
            selected_element_id = self._selected_episode_element_id()
        self.process_elements = EpisodeStateService().calculate_episode_state(
            self.episode["epizod_id"]
        )["elements"]
        self.tasks = list_episode_tasks(self.episode["epizod_id"])
        self._populate_process_overview_table()
        if selected_element_id is not None and self._process_overview_table is not None:
            for row_index in range(self._process_overview_table.rowCount()):
                item = self._process_overview_table.item(row_index, 0)
                if (
                    item is not None
                    and item.data(Qt.ItemDataRole.UserRole) == selected_element_id
                ):
                    self._process_overview_table.selectRow(row_index)
                    break
        self.update_episode_path_buttons()

    def refresh_from_eskulap(self):
        self.btn_refresh_episode.setEnabled(False)
        self._refresh_selected_element_id = self._selected_episode_element_id()
        show_busy("Aktualizowanie danych z Eskulapa...", self)

        self._refresh_thread = QThread(self)
        self._refresh_worker = EpisodeRefreshWorker(self.episode["epizod_id"])
        self._refresh_worker.moveToThread(self._refresh_thread)
        self._refresh_thread.started.connect(self._refresh_worker.run)
        self._refresh_worker.finished.connect(self._episode_refresh_finished)
        self._refresh_worker.failed.connect(self._episode_refresh_failed)
        self._refresh_worker.finished.connect(self._refresh_thread.quit)
        self._refresh_worker.failed.connect(self._refresh_thread.quit)
        self._refresh_worker.finished.connect(self._refresh_worker.deleteLater)
        self._refresh_worker.failed.connect(self._refresh_worker.deleteLater)
        self._refresh_thread.finished.connect(self._refresh_thread.deleteLater)
        self._refresh_thread.finished.connect(self._episode_refresh_cleanup)
        self._refresh_thread.start()

    def _episode_refresh_finished(self, summary):
        self._refresh_process(self._refresh_selected_element_id)
        if summary.errors:
            log_path = configure_application_logging() or application_log_path()
            QMessageBox.warning(
                self,
                "KOMPAS",
                "Odświeżenie epizodu zakończyło się z ostrzeżeniami. "
                "Szczegóły zapisano w logu:\n\n"
                f"{log_path}",
            )
            logger.warning(
                "Odświeżenie epizodu %s: %s",
                self.episode["epizod_id"],
                summary.errors,
            )
        else:
            QMessageBox.information(
                self,
                "KOMPAS",
                "Dane epizodu zostały odświeżone z Eskulapa.",
            )

    def _episode_refresh_failed(self, message):
        log_path = configure_application_logging() or application_log_path()
        logger.error(
            "Nie udało się odświeżyć epizodu %s z Eskulapa: %s",
            self.episode["epizod_id"],
            message,
        )
        QMessageBox.critical(
            self,
            "KOMPAS",
            "Nie udało się odświeżyć danych z Eskulapa. "
            "Szczegóły techniczne zapisano w logu:\n\n"
            f"{log_path}",
        )

    def _episode_refresh_cleanup(self):
        hide_busy(self)
        self.btn_refresh_episode.setEnabled(True)
        self._refresh_thread = None
        self._refresh_worker = None
        self._refresh_selected_element_id = None

    def _ask_reason(self, title, label):
        value, accepted = QInputDialog.getMultiLineText(
            self,
            title,
            label,
        )
        if not accepted:
            return None
        return value.strip()

    def plan_selected_element(self):
        element = self._selected_episode_element()
        if element is None:
            QMessageBox.information(
                self,
                "KOMPAS",
                "Najpierw zaznacz konsultację albo badanie obrazowe.",
            )
            return
        check = episode_path_service.can_plan_element(
            element["epizod_element_id"]
        )
        if not check.get("allowed"):
            QMessageBox.warning(
                self,
                "KOMPAS",
                check.get("reason") or "Tego elementu nie można zaplanować.",
            )
            return
        dialog = EpisodeElementPlanningDialog(element, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        try:
            episode_path_service.plan_episode_element(
                element["epizod_element_id"],
                values["plan_date"],
                values["time_from"],
                values["time_to"],
                values["notes"],
                self.current_user,
            )
            self._refresh_process(element["epizod_element_id"])
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się zaplanować elementu:\n\n{exc}",
            )

    def clear_selected_element_plan(self):
        element = self._selected_episode_element()
        if element is None:
            QMessageBox.information(
                self,
                "KOMPAS",
                "Najpierw zaznacz element z terminem KOMPAS.",
            )
            return
        if QMessageBox.question(
            self,
            "KOMPAS",
            "Usunąć lokalny termin KOMPAS dla zaznaczonego elementu?",
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            episode_path_service.clear_episode_element_plan(
                element["epizod_element_id"],
                self.current_user,
            )
            self._refresh_process(element["epizod_element_id"])
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się usunąć terminu:\n\n{exc}",
            )

    def deactivate_selected_element(self):
        element_id = self._selected_episode_element_id()
        if element_id is None:
            QMessageBox.information(
                self,
                "KOMPAS",
                "Najpierw zaznacz element procesu w tabeli Elementy procesu.",
            )
            return
        check = episode_path_service.can_deactivate_element(element_id)
        if not check.get("allowed"):
            QMessageBox.warning(
                self,
                "KOMPAS",
                check.get("reason") or "Elementu nie można dezaktywować.",
            )
            return
        reason = self._ask_reason(
            "Dezaktywuj element",
            "Podaj przyczynę dezaktywacji elementu:",
        )
        if reason is None:
            return
        if QMessageBox.question(
            self,
            "KOMPAS",
            "Niezrealizowane zadania powiązane z elementem zostaną anulowane. "
            "Kontynuować?",
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            episode_path_service.deactivate_element(
                element_id,
                reason,
                self.current_user,
            )
            self._refresh_process()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się dezaktywować elementu:\n\n{exc}",
            )

    def reactivate_selected_element(self):
        element_id = self._selected_episode_element_id()
        if element_id is None:
            QMessageBox.information(
                self,
                "KOMPAS",
                "Najpierw zaznacz element procesu w tabeli Elementy procesu.",
            )
            return
        reason = self._ask_reason(
            "Reaktywuj element",
            "Podaj przyczynę reaktywacji elementu:",
        )
        if reason is None:
            return
        create_task = QMessageBox.question(
            self,
            "KOMPAS",
            "Czy utworzyć nowe zadanie dla reaktywowanego elementu?",
        ) == QMessageBox.StandardButton.Yes
        try:
            episode_path_service.reactivate_element(
                element_id,
                reason,
                self.current_user,
                create_task=create_task,
            )
            self._refresh_process()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się reaktywować elementu:\n\n{exc}",
            )

    def duplicate_selected_element(self):
        element = self._selected_episode_element()
        if element is None:
            QMessageBox.information(
                self,
                "KOMPAS",
                "Najpierw zaznacz element procesu w tabeli Elementy procesu.",
            )
            return
        dialog = EpisodeElementDuplicateDialog(element, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values, reason = dialog.values()
        try:
            episode_path_service.duplicate_element(
                element["epizod_element_id"],
                values,
                reason,
                self.current_user,
            )
            self._refresh_process()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"Nie udało się powielić elementu:\n\n{exc}",
            )

    def show_selected_element_history(self):
        element_id = self._selected_episode_element_id()
        if element_id is None:
            QMessageBox.information(
                self,
                "KOMPAS",
                "Najpierw zaznacz element procesu w tabeli Elementy procesu.",
            )
            return
        rows = episode_path_service.list_element_history(element_id)
        text = "\n\n".join(
            f"{row['changed_at']} — {row['operacja']}\n"
            f"Użytkownik: {row['changed_by'] or 'brak'}\n"
            f"Powód: {row['powod'] or 'brak'}"
            for row in rows
        ) or "Brak historii zmian."
        QMessageBox.information(self, "Historia zmian elementu", text)
