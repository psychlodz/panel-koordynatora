import platform
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.repositories.db_connection import load_database_settings
from app.ui.ui_helpers import create_help_button
from app.ui.users_window import UsersWindow
from config import app_dir
from version import APP_NAME, BUILD, VERSION


PLACEHOLDER_NEXT_VERSIONS = (
    "Funkcja będzie dostępna w kolejnych wersjach."
)
PLACEHOLDER_CONFIGURATION = (
    "Konfiguracja zostanie udostępniona w kolejnych wersjach."
)


TAB_DEFINITIONS = (
    (
        "Słowniki",
        "Centralny katalog danych biznesowych, systemowych i referencyjnych.",
    ),
    (
        "Integracja Eskulap",
        "Konfiguracja mapowań i diagnostyki integracji z Eskulapem.",
    ),
    (
        "Parametry systemu",
        "Parametry działania interfejsu i modułów KOMPAS.",
    ),
    (
        "Role i uprawnienia",
        "Zarządzanie użytkownikami, rolami oraz dostępem do jednostek.",
    ),
    (
        "Diagnostyka",
        "Narzędzia kontroli połączeń, wersji i logów aplikacji.",
    ),
    (
        "Harmonogram usług",
        "Konfiguracja automatycznych synchronizacji i zadań cyklicznych.",
    ),
    (
        "Powiadomienia",
        "Konfiguracja kanałów oraz reguł powiadamiania.",
    ),
    (
        "Informacje o systemie",
        "Informacje techniczne o uruchomionej instalacji KOMPAS.",
    ),
)


class SystemSettingsWindow(QWidget):
    def __init__(self, current_user, parent=None):
        if not current_user or not current_user.is_admin:
            raise PermissionError(
                "Dostęp do ustawień systemu wymaga roli ADMIN"
            )
        super().__init__(parent)
        self.current_user = current_user
        self.setWindowTitle(f"{APP_NAME} — Ustawienia systemu")
        self.resize(1450, 880)
        self.setMinimumSize(1050, 680)

        layout = QVBoxLayout(self)
        title = QLabel("Ustawienia systemu")
        title.setObjectName("sectionTitle")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Administracja konfiguracją KOMPAS. Kody systemowe są "
            "chronione i nie podlegają swobodnej edycji."
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        layout.addWidget(self.tabs, 1)

        self.tabs.addTab(self._dictionaries_tab(), "Słowniki")
        self.tabs.addTab(
            self._placeholder_tab(
                "Integracja Eskulap",
                TAB_DEFINITIONS[1][1],
                (
                    "Filtr wizyty kwalifikacyjnej",
                    "Mapowanie badań",
                    "Mapowanie konsultacji",
                    "Mapowanie procedur",
                    "Mapowanie produktów",
                    "Mapowanie zdarzeń",
                    "Diagnostyka Gateway",
                ),
                PLACEHOLDER_NEXT_VERSIONS,
            ),
            "Integracja Eskulap",
        )
        self.tabs.addTab(
            self._placeholder_tab(
                "Parametry systemu",
                TAB_DEFINITIONS[2][1],
                (
                    "Domyślna liczba miesięcy harmonogramu",
                    "Domyślna jednostka",
                    "Ustawienia Dashboardów",
                    "Ustawienia kolorystyki",
                    "Ustawienia eksportów",
                    "Ustawienia wydruków",
                ),
                PLACEHOLDER_CONFIGURATION,
            ),
            "Parametry systemu",
        )
        self.tabs.addTab(
            self._roles_tab(),
            "Role i uprawnienia",
        )
        self.tabs.addTab(
            self._placeholder_tab(
                "Diagnostyka",
                TAB_DEFINITIONS[4][1],
                (
                    "Test Gateway",
                    "Test Oracle",
                    "Test PostgreSQL",
                    "Wersja aplikacji",
                    "Wersja bazy",
                    "Logi",
                ),
                PLACEHOLDER_NEXT_VERSIONS,
            ),
            "Diagnostyka",
        )
        self.tabs.addTab(
            self._placeholder_tab(
                "Harmonogram usług",
                TAB_DEFINITIONS[5][1],
                (
                    "Synchronizacja z Eskulapem",
                    "Zadania cykliczne",
                    "Odświeżanie Dashboardów",
                ),
                PLACEHOLDER_NEXT_VERSIONS,
            ),
            "Harmonogram usług",
        )
        self.tabs.addTab(
            self._placeholder_tab(
                "Powiadomienia",
                TAB_DEFINITIONS[6][1],
                (
                    "SMTP",
                    "E-mail",
                    "SMS",
                    "Komunikaty",
                ),
                PLACEHOLDER_NEXT_VERSIONS,
            ),
            "Powiadomienia",
        )
        self.tabs.addTab(
            self._system_information_tab(),
            "Informacje o systemie",
        )

    def _page(self, title, description, help_text):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        heading = QLabel(title)
        heading.setStyleSheet("font-size: 17px; font-weight: bold;")
        layout.addWidget(heading)

        description_label = QLabel(description)
        description_label.setWordWrap(True)
        description_label.setObjectName("settingsTabDescription")
        layout.addWidget(description_label)

        page._settings_layout = layout
        page._settings_help_text = help_text
        page._settings_title = title
        return page

    def _add_footer(self, page):
        footer = QHBoxLayout()
        help_button = create_help_button(
            self,
            page._settings_title,
            page._settings_help_text,
        )
        close_button = QPushButton("Zamknij")
        close_button.setProperty("role", "secondary")
        close_button.setToolTip("Zamknij okno Ustawień systemu.")
        close_button.clicked.connect(self.close)
        footer.addWidget(help_button)
        footer.addStretch(1)
        footer.addWidget(close_button)
        page._settings_layout.addLayout(footer)

    @staticmethod
    def _dictionary_group(title, rows):
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        tree = QTreeWidget()
        tree.setColumnCount(3)
        tree.setHeaderLabels(["Pozycja", "Tryb", "Źródło"])
        tree.setRootIsDecorated(False)
        tree.setAlternatingRowColors(True)
        tree.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        for name, mode, source in rows:
            QTreeWidgetItem(tree, [name, mode, source])
        tree.header().setStretchLastSection(True)
        tree.resizeColumnToContents(0)
        tree.resizeColumnToContents(1)
        layout.addWidget(tree)
        return group

    def _dictionaries_tab(self):
        title, description = TAB_DEFINITIONS[0]
        page = self._page(
            title,
            description,
            "Zakładka porządkuje słowniki KOMPAS według ich źródła "
            "i zakresu przyszłej edycji. Dane systemowe oraz dane "
            "referencyjne Eskulapa pozostają tylko do odczytu.",
        )
        page._settings_layout.addWidget(
            self._dictionary_group(
                "A. Dane biznesowe",
                (
                    (
                        "Typy elementów procesu",
                        "Edycja w kolejnym sprincie",
                        "Baza KOMPAS",
                    ),
                    (
                        "Biblioteka klocków",
                        "Edycja w kolejnym sprincie",
                        "Baza KOMPAS",
                    ),
                    (
                        "Grupy klocków",
                        "W przygotowaniu",
                        "Baza KOMPAS",
                    ),
                    (
                        "Jednostki czasu",
                        "W przygotowaniu",
                        "Baza KOMPAS",
                    ),
                    (
                        "Statusy biznesowe",
                        "Docelowo",
                        "Baza KOMPAS",
                    ),
                ),
            ),
            1,
        )
        page._settings_layout.addWidget(
            self._dictionary_group(
                "B. Dane systemowe — tylko podgląd",
                (
                    ("Typy wyzwalaczy", "Tylko podgląd", "Kod systemu"),
                    ("Typy zależności", "Tylko podgląd", "Kod systemu"),
                    ("Źródła danych", "Tylko podgląd", "Kod systemu"),
                    (
                        "Statusy synchronizacji",
                        "Tylko podgląd",
                        "Kod systemu",
                    ),
                    ("Role systemowe", "Tylko podgląd", "Baza KOMPAS"),
                ),
            ),
            1,
        )
        page._settings_layout.addWidget(
            self._dictionary_group(
                "C. Dane referencyjne Eskulapa — tylko odczyt",
                (
                    (
                        "Jednostki organizacyjne",
                        "Tylko odczyt",
                        "Eskulap Gateway",
                    ),
                    (
                        "Typy konsultacji",
                        "Tylko odczyt",
                        "Eskulap Gateway",
                    ),
                    (
                        "Typy badań",
                        "Tylko odczyt",
                        "Eskulap Gateway",
                    ),
                ),
            ),
            1,
        )
        self._add_footer(page)
        return page

    def _placeholder_tab(
        self,
        title,
        description,
        items,
        placeholder_message,
    ):
        page = self._page(
            title,
            description,
            f"{description}\n\n{placeholder_message}",
        )
        group = QGroupBox("Planowany zakres")
        group_layout = QVBoxLayout(group)
        for item in items:
            label = QLabel(f"• {item}")
            label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            group_layout.addWidget(label)
        group_layout.addStretch(1)
        page._settings_layout.addWidget(group, 1)

        message = QLabel(placeholder_message)
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setWordWrap(True)
        message.setStyleSheet(
            "font-size: 12pt; font-weight: 600; padding: 18px;"
        )
        page._settings_layout.addWidget(message)
        self._add_footer(page)
        return page

    def _roles_tab(self):
        title, description = TAB_DEFINITIONS[3]
        page = self._page(
            title,
            description,
            "Tutaj administrator zarządza użytkownikami KOMPAS, "
            "przypisanymi rolami i jednostkami organizacyjnymi. "
            "Nie należy usuwać dostępu ostatniemu administratorowi.",
        )
        users_widget = UsersWindow(self.current_user, page)
        page._settings_layout.addWidget(users_widget, 1)
        self._add_footer(page)
        return page

    @staticmethod
    def _safe_database_settings():
        try:
            return load_database_settings()
        except Exception:
            return None

    def _system_information_tab(self):
        title, description = TAB_DEFINITIONS[7]
        page = self._page(
            title,
            description,
            "Zakładka pokazuje metadane uruchomionej instalacji. "
            "Nie zmienia konfiguracji ani danych systemu.",
        )
        settings = self._safe_database_settings()
        database_engine = (
            settings.engine.upper() if settings is not None else "nieznany"
        )
        postgres_version = (
            "Niewykryta — test połączenia będzie dostępny w Diagnostyce"
            if settings is not None and settings.engine == "postgres"
            else "Nie dotyczy bieżącego trybu"
        )
        build_date = (
            "Data pliku wykonywalnego"
            if getattr(sys, "frozen", False)
            else "Tryb deweloperski — brak daty kompilacji"
        )
        if getattr(sys, "frozen", False):
            try:
                from datetime import datetime

                build_date = datetime.fromtimestamp(
                    Path(sys.executable).stat().st_mtime
                ).strftime("%Y-%m-%d %H:%M:%S")
            except OSError:
                build_date = "brak danych"

        group = QGroupBox("Metadane")
        form = QFormLayout(group)
        values = (
            ("Wersja KOMPAS:", f"{VERSION} (build {BUILD})"),
            (
                "Wersja bazy:",
                f"{database_engine}; schemat bez rejestru wersji",
            ),
            ("Wersja Gateway:", f"Wbudowany w KOMPAS {VERSION}"),
            ("Wersja Python:", platform.python_version()),
            ("Wersja PostgreSQL:", postgres_version),
            ("Data kompilacji:", build_date),
            (
                "Ścieżka do konfiguracji:",
                str(Path(app_dir()) / "config.ini"),
            ),
        )
        for label, value in values:
            value_label = QLabel(value)
            value_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            value_label.setWordWrap(True)
            form.addRow(label, value_label)
        page._settings_layout.addWidget(group, 1)
        self._add_footer(page)
        return page


__all__ = ["SystemSettingsWindow", "TAB_DEFINITIONS"]
