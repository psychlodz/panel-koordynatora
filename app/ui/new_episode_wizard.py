from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from app.repositories.pathway_repository import list_pathways
from app.repositories.program_repository import list_programs
from episode_generator import create_episode_with_tasks
from pathway_service import list_episode_tasks


class EpisodeWizard(QWizard):
    PATIENT_PAGE = 0
    PROGRAM_PAGE = 1
    PATHWAY_PAGE = 2
    COORDINATOR_PAGE = 3
    START_PAGE = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("KOMPAS — Nowy epizod")
        self.resize(680, 430)
        self.setButtonText(
            QWizard.WizardButton.FinishButton,
            "Rozpocznij",
        )

        self.patient_edit = QLineEdit()
        self.patient_edit.setPlaceholderText(
            "Identyfikator pacjenta z Oracle/Eskulapa"
        )
        self.program_combo = QComboBox()
        self.pathway_combo = QComboBox()
        self.coordinator_edit = QLineEdit()
        self.coordinator_edit.setPlaceholderText(
            "Opcjonalny identyfikator koordynatora"
        )
        self.start_date_edit = QDateEdit(QDate.currentDate())
        self.start_date_edit.setCalendarPopup(True)
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)

        self.addPage(self._patient_page())
        self.addPage(self._program_page())
        self.addPage(self._pathway_page())
        self.addPage(self._coordinator_page())
        self.addPage(self._start_page())

        self._load_programs()

    @staticmethod
    def _page(title, subtitle=None):
        page = QWizardPage()
        page.setTitle(title)
        if subtitle:
            page.setSubTitle(subtitle)
        page.setLayout(QVBoxLayout())
        return page

    def _patient_page(self):
        page = self._page(
            "1. Pacjent z Oracle",
            "Wprowadź identyfikator pacjenta pochodzący z Oracle/Eskulapa.",
        )
        form = QFormLayout()
        form.addRow("ID pacjenta:", self.patient_edit)
        page.layout().addLayout(form)
        page.layout().addStretch(1)
        return page

    def _program_page(self):
        page = self._page(
            "2. Program",
            "Wybierz aktywny program KOMPAS.",
        )
        form = QFormLayout()
        form.addRow("Program:", self.program_combo)
        page.layout().addLayout(form)
        page.layout().addStretch(1)
        return page

    def _pathway_page(self):
        page = self._page(
            "3. Ścieżka",
            "Wybierz aktywną ścieżkę dla programu.",
        )
        form = QFormLayout()
        form.addRow("Ścieżka:", self.pathway_combo)
        page.layout().addLayout(form)
        page.layout().addStretch(1)
        return page

    def _coordinator_page(self):
        page = self._page(
            "4. Koordynator",
            "Przypisanie koordynatora jest opcjonalne.",
        )
        form = QFormLayout()
        form.addRow("ID koordynatora:", self.coordinator_edit)
        page.layout().addLayout(form)
        page.layout().addStretch(1)
        return page

    def _start_page(self):
        page = self._page(
            "5. Start",
            "Sprawdź dane i rozpocznij epizod.",
        )
        form = QFormLayout()
        form.addRow("Data rozpoczęcia:", self.start_date_edit)
        page.layout().addLayout(form)
        page.layout().addWidget(self.summary_label)
        page.layout().addStretch(1)
        return page

    def _load_programs(self):
        self.program_combo.clear()
        for program in list_programs():
            if program["czy_aktywny"]:
                self.program_combo.addItem(
                    f"{program['kod']} — {program['nazwa']}",
                    program["program_id"],
                )

    def _load_pathways(self):
        self.pathway_combo.clear()
        program_id = self.program_combo.currentData()
        if program_id is None:
            return
        for pathway in list_pathways(program_id):
            if pathway["czy_aktywna"]:
                self.pathway_combo.addItem(
                    f"{pathway['kod']} — {pathway['nazwa']}",
                    pathway["sciezka_id"],
                )

    def _update_summary(self):
        coordinator = self.coordinator_edit.text().strip() or "Nie przypisano"
        self.summary_label.setText(
            "<b>Podsumowanie</b><br>"
            f"Pacjent: {self.patient_edit.text().strip()}<br>"
            f"Program: {self.program_combo.currentText()}<br>"
            f"Ścieżka: {self.pathway_combo.currentText()}<br>"
            f"Koordynator: {coordinator}"
        )

    def initializePage(self, page_id):
        super().initializePage(page_id)
        if page_id == self.PATHWAY_PAGE:
            self._load_pathways()
        elif page_id == self.START_PAGE:
            self._update_summary()

    def validateCurrentPage(self):
        page_id = self.currentId()
        if page_id == self.PATIENT_PAGE and not self.patient_edit.text().strip():
            QMessageBox.warning(
                self,
                "KOMPAS",
                "Identyfikator pacjenta jest wymagany.",
            )
            return False
        if page_id == self.PROGRAM_PAGE:
            if self.program_combo.currentData() is None:
                QMessageBox.warning(
                    self,
                    "KOMPAS",
                    "Brak aktywnego programu do wyboru.",
                )
                return False
        if page_id == self.PATHWAY_PAGE:
            if self.pathway_combo.currentData() is None:
                QMessageBox.warning(
                    self,
                    "KOMPAS",
                    "Brak aktywnej ścieżki dla wybranego programu.",
                )
                return False
        return super().validateCurrentPage()

    def accept(self):
        try:
            epizod_id = create_episode_with_tasks(
                pacjent_id=self.patient_edit.text().strip(),
                program_id=self.program_combo.currentData(),
                sciezka_id=self.pathway_combo.currentData(),
                data_start=self.start_date_edit.date().toString("yyyy-MM-dd"),
                koordynator_id=(
                    self.coordinator_edit.text().strip() or None
                ),
            )
            task_count = len(list_episode_tasks(epizod_id))
        except Exception as exc:
            QMessageBox.critical(
                self,
                "KOMPAS",
                f"""Nie udało się rozpocząć epizodu:

{exc}""",
            )
            return

        QMessageBox.information(
            self,
            "KOMPAS",
            f"""Utworzono epizod {epizod_id}.
Aktywne zadania: {task_count}.""",
        )
        super().accept()
