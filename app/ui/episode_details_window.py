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
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from app.gateway.eskulap_gateway import EskulapGateway
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
from app.ui.ui_helpers import create_help_button, polish_dialog_buttons
from app.services import episode_path_service
from app.services.work_context import work_context


WAITING_STATUS = "OCZEKUJE NA AKTYWACJĘ"
CONTACT_TOOLTIP = (
    "Dane kontaktowe są pobierane z Eskulapa i nie są zapisywane w KOMPAS."
)


def _text(value):
    return "" if value is None else str(value)


def _eskulap_visit_text(record):
    parts = []
    for field_name in (
        "eskulap_pracownik",
        "eskulap_data_wizyty",
        "eskulap_rodzaj_wizyty",
    ):
        value = record.get(field_name)
        if value:
            parts.append(str(value))
    return "\n".join(parts) if parts else ""


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


def _event_date_key(event):
    value = event.event_date
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    return datetime.min


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
        self.current_user = work_context.current_user
        self._process_overview_table = None
        self._process_tasks_table = None

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
            "To okno przedstawia dane epizodu, zadania i zdarzenia "
            "medyczne z Eskulapa.\n\n"
            "Możesz przeglądać proces, konsultacje, badania, wizyty i "
            "historię. Uprawnieni użytkownicy mogą także powielić, "
            "dezaktywować albo reaktywować element procesu wyłącznie w tym "
            "epizodzie.\n\n"
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

        table = QTableWidget(len(self.process_elements), 5)
        self._process_overview_table = table
        table.setHorizontalHeaderLabels(
            ["Element procesu", "Status", "Termin", "Realizacja", "Wizyta Eskulap"]
        )
        _configure_table(table, 0)
        self._populate_process_overview_table()
        layout.addWidget(table)
        return panel

    def _populate_process_overview_table(self):
        table = self._process_overview_table
        if table is None:
            return
        table.setRowCount(len(self.process_elements))
        for row_index, element in enumerate(self.process_elements):
            name = element["nazwa_w_sciezce"] or element["klocek_nazwa"]
            if not element.get("czy_aktywny", 1):
                name = f"{name} [Dezaktywowany]"
            elif element.get("typ_pochodzenia") == "POWIELENIE":
                name = f"{name} [Powielenie]"
            values = [
                name,
                element["status"] or WAITING_STATUS,
                element["data_wymagana_do"] or element["data_zaplanowana"],
                element["data_realizacji"],
                _eskulap_visit_text(element),
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(_text(value))
                item.setData(
                    Qt.ItemDataRole.UserRole,
                    element.get("epizod_element_id"),
                )
                if column_index in (1, 2, 3):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignLeft
                        | Qt.AlignmentFlag.AlignVCenter
                    )
                    item.setToolTip(_text(value))
                table.setItem(
                    row_index,
                    column_index,
                    item,
                )

    def _process_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        actions = QHBoxLayout()
        self.btn_duplicate_element = QPushButton("Powiel element")
        self.btn_duplicate_element.setToolTip(
            "Utwórz dodatkowe wykonanie wybranego elementu tylko w tym epizodzie."
        )
        self.btn_deactivate_element = QPushButton("Dezaktywuj element")
        self.btn_deactivate_element.setToolTip(
            "Wyłącz wybrany element w tym epizodzie bez usuwania go z historii."
        )
        self.btn_reactivate_element = QPushButton("Reaktywuj element")
        self.btn_reactivate_element.setToolTip(
            "Przywróć dezaktywowany element w tym epizodzie."
        )
        self.btn_history_element = QPushButton("Historia zmian")
        self.btn_history_element.setToolTip(
            "Pokaż historię zmian wybranego elementu epizodu."
        )
        self.btn_duplicate_element.clicked.connect(self.duplicate_selected_element)
        self.btn_deactivate_element.clicked.connect(self.deactivate_selected_element)
        self.btn_reactivate_element.clicked.connect(self.reactivate_selected_element)
        self.btn_history_element.clicked.connect(self.show_selected_element_history)
        for button in (
            self.btn_duplicate_element,
            self.btn_deactivate_element,
            self.btn_reactivate_element,
            self.btn_history_element,
        ):
            actions.addWidget(button)
        actions.addStretch(1)
        layout.addLayout(actions)

        table = QTableWidget(len(self.tasks), 8)
        self._process_tasks_table = table
        table.setHorizontalHeaderLabels(
            [
                "Nazwa elementu",
                "Status",
                "Data wymagana do",
                "Zaplanowano",
                "Realizacja",
                "Wizyta Eskulap",
                "Źródło",
                "Uwagi",
            ]
        )
        _configure_table(table, 0)
        table.itemSelectionChanged.connect(self.update_episode_path_buttons)
        self._populate_tasks_table()
        layout.addWidget(table)
        self.update_episode_path_buttons()
        return tab

    def _populate_tasks_table(self):
        table = self._process_tasks_table
        if table is None:
            return
        table.setRowCount(len(self.tasks))
        for row_index, task in enumerate(self.tasks):
            values = [
                task["nazwa_w_sciezce"] or task["klocek_nazwa"],
                task["status"],
                task["data_wymagana_do"],
                task["data_zaplanowana"],
                task["data_realizacji"],
                _eskulap_visit_text(task),
                task["zrodlo"],
                task["uwagi"],
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(_text(value))
                item.setData(
                    Qt.ItemDataRole.UserRole,
                    task.get("epizod_element_id"),
                )
                if column_index in (1, 2, 3, 4, 6):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignLeft
                        | Qt.AlignmentFlag.AlignVCenter
                    )
                    item.setToolTip(_text(value))
                table.setItem(
                    row_index,
                    column_index,
                    item,
                )

    def _selected_episode_element_id(self):
        for table in (
            self._process_tasks_table,
            self._process_overview_table,
        ):
            if table is None:
                continue
            row = table.currentRow()
            if row < 0:
                continue
            item = table.item(row, 0)
            if item is None:
                continue
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
            self.btn_deactivate_element,
            self.btn_reactivate_element,
            self.btn_history_element,
        ):
            button.setEnabled(selected and can_edit)
        self.btn_history_element.setEnabled(selected)
        if not can_edit:
            tooltip = "Operacja wymaga uprawnienia EPISODE_PATH_EDIT."
            self.btn_duplicate_element.setToolTip(tooltip)
            self.btn_deactivate_element.setToolTip(tooltip)
            self.btn_reactivate_element.setToolTip(tooltip)
            return
        if element:
            is_active = bool(element.get("czy_aktywny", 1))
            self.btn_deactivate_element.setEnabled(is_active)
            self.btn_reactivate_element.setEnabled(not is_active)

    def _refresh_process(self):
        self.process_elements = list_episode_process_elements(
            self.episode["epizod_id"]
        )
        self.tasks = list_episode_tasks(self.episode["epizod_id"])
        self._populate_process_overview_table()
        self._populate_tasks_table()
        self.update_episode_path_buttons()

    def _ask_reason(self, title, label):
        value, accepted = QInputDialog.getMultiLineText(
            self,
            title,
            label,
        )
        if not accepted:
            return None
        return value.strip()

    def deactivate_selected_element(self):
        element_id = self._selected_episode_element_id()
        if element_id is None:
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
            return
        rows = episode_path_service.list_element_history(element_id)
        text = "\n\n".join(
            f"{row['changed_at']} — {row['operacja']}\n"
            f"Użytkownik: {row['changed_by'] or 'brak'}\n"
            f"Powód: {row['powod'] or 'brak'}"
            for row in rows
        ) or "Brak historii zmian."
        QMessageBox.information(self, "Historia zmian elementu", text)

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
                item = QTableWidgetItem(_text(value))
                if column_index in (0, 1, 2, 3, 5):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignLeft
                        | Qt.AlignmentFlag.AlignVCenter
                    )
                    item.setToolTip(_text(value))
                table.setItem(
                    row_index,
                    column_index,
                    item,
                )
        layout.addWidget(table)
        return tab
