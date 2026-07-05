import platform
import re
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.repositories.db_connection import load_database_settings
from app.repositories.dependency_repository import DEPENDENCY_TYPES
from app.repositories.system_settings_repository import (
    get_business_dictionaries,
)
from app.repositories.trigger_repository import TRIGGER_TYPES
from app.repositories.qualification_repository import (
    PKK_KWAL_PARAMETR_KOD,
)
from app.ui.ui_helpers import create_help_button
from app.ui.users_window import UsersWindow
from config import app_dir, load_config
from version import APP_NAME, BUILD, VERSION


MIGRATION_PENDING = "Słownik zaprojektowany, oczekuje na migrację bazy."
PREPARATION_MESSAGE = "W przygotowaniu"
LOGS_DIRNAME = "logs"

TAB_DEFINITIONS = (
    (
        "Słowniki",
        "Podgląd słowników biznesowych, systemowych i danych "
        "referencyjnych Eskulapa.",
    ),
    (
        "Integracja Eskulap",
        "Informacje o filtrach, widokach i planowanych mapowaniach "
        "integracyjnych.",
    ),
    (
        "Parametry systemu",
        "Bezpieczny podgląd bieżącej konfiguracji KOMPAS.",
    ),
    (
        "Role i uprawnienia",
        "Zarządzanie użytkownikami, rolami oraz dostępem do jednostek.",
    ),
    (
        "Diagnostyka",
        "Instrukcje testów połączeń i dostęp do katalogów technicznych.",
    ),
    (
        "Informacje o systemie",
        "Podstawowe informacje o uruchomionej instalacji KOMPAS.",
    ),
)


def _readable_engine(settings):
    if settings is None:
        return "Nieznany"
    return "PostgreSQL"


def _safe_postgres_dsn(settings):
    if settings is None or settings.engine != "postgres":
        return "Nie dotyczy bieżącego trybu"
    value = str(settings.postgres_dsn or "").strip()
    if not value:
        return "Nie skonfigurowano"
    value = re.sub(
        r"(?i)\bpassword\s*=\s*(?:'[^']*'|\"[^\"]*\"|[^\s]+)",
        "password=<ukryte>",
        value,
    )
    value = re.sub(
        r"(?i)(://[^:/@\s]+):[^@\s]+@",
        r"\1@",
        value,
    )
    value = re.sub(
        r"(?i)([?&]password=)[^&]*",
        r"\1<ukryte>",
        value,
    )
    return value


class SystemSettingsWindow(QWidget):
    def __init__(self, current_user, parent=None):
        if not current_user or not current_user.is_admin:
            raise PermissionError(
                "Dostęp do ustawień systemu wymaga roli ADMIN"
            )
        super().__init__(parent)
        self.current_user = current_user
        self.application_dir = Path(app_dir())
        self.config_path = self.application_dir / "config.ini"
        self.logs_path = self.application_dir / LOGS_DIRNAME
        self.database_settings = self._database_settings()

        self.setWindowTitle(f"{APP_NAME} - Ustawienia systemu")
        self.resize(1450, 880)
        self.setMinimumSize(1050, 680)

        layout = QVBoxLayout(self)
        title = QLabel("Ustawienia systemu")
        title.setObjectName("sectionTitle")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Centralne miejsce administracji konfiguracją KOMPAS. "
            "Kody systemowe i dane Eskulapa pozostają tylko do odczytu."
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._dictionaries_tab(), "Słowniki")
        self.tabs.addTab(
            self._eskulap_integration_tab(),
            "Integracja Eskulap",
        )
        self.tabs.addTab(
            self._system_parameters_tab(),
            "Parametry systemu",
        )
        self.tabs.addTab(self._roles_tab(), "Role i uprawnienia")
        self.tabs.addTab(self._diagnostics_tab(), "Diagnostyka")
        self.tabs.addTab(
            self._system_information_tab(),
            "Informacje o systemie",
        )
        layout.addWidget(self.tabs, 1)

    @staticmethod
    def _database_settings():
        try:
            return load_database_settings()
        except Exception:
            return None

    @staticmethod
    def _application_config():
        try:
            return load_config()
        except Exception:
            return None

    def _page(self, title, description, help_text):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        heading = QLabel(title)
        heading.setStyleSheet("font-size: 17px; font-weight: bold;")
        layout.addWidget(heading)

        description_label = QLabel(description)
        description_label.setObjectName("settingsTabDescription")
        description_label.setWordWrap(True)
        layout.addWidget(description_label)

        page._settings_layout = layout
        page._settings_title = title
        page._settings_help_text = help_text
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
    def _tree(headers):
        tree = QTreeWidget()
        tree.setColumnCount(len(headers))
        tree.setHeaderLabels(headers)
        tree.setAlternatingRowColors(True)
        tree.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        tree.header().setStretchLastSection(True)
        return tree

    def _business_dictionaries_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        tree = self._tree(
            ["Słownik / kod", "Nazwa", "Typ", "Aktywny", "Opis"]
        )
        try:
            data = get_business_dictionaries()
            types_node = QTreeWidgetItem(
                tree,
                ["Typy elementów procesu", "", "", "", ""],
            )
            for item in data["element_types"]:
                QTreeWidgetItem(
                    types_node,
                    [item["kod"], item["nazwa"], "", "Tak", ""],
                )

            blocks_node = QTreeWidgetItem(
                tree,
                ["Biblioteka klocków", "", "", "", ""],
            )
            for item in data["blocks"]:
                QTreeWidgetItem(
                    blocks_node,
                    [
                        item["kod"],
                        item["nazwa"],
                        item["typ"],
                        "Tak" if item["czy_aktywny"] else "Nie",
                        item["opis"] or "",
                    ],
                )

            groups_node = QTreeWidgetItem(
                tree, ["Grupy klocków", "", "", "", ""]
            )
            for item in data["block_groups"]:
                QTreeWidgetItem(
                    groups_node,
                    [
                        item["kod"],
                        item["nazwa"],
                        "Grupa",
                        "Tak" if item["czy_aktywny"] else "Nie",
                        item["opis"] or "",
                    ],
                )

            time_node = QTreeWidgetItem(
                tree, ["Jednostki czasu", "", "", "", ""]
            )
            for item in data["time_units"]:
                QTreeWidgetItem(
                    time_node,
                    [
                        item["kod"],
                        item["nazwa"],
                        (
                            f"{item['rodzaj_obliczenia']} × "
                            f"{item['mnoznik']}"
                        ),
                        "Tak" if item["czy_aktywny"] else "Nie",
                        item["opis"] or "",
                    ],
                )
        except Exception:
            QTreeWidgetItem(
                tree,
                [
                    "Nie udało się pobrać słowników",
                    "Sprawdź połączenie z bazą KOMPAS",
                    "",
                    "",
                    "",
                ],
            )
        tree.expandAll()
        for column in range(4):
            tree.resizeColumnToContents(column)
        layout.addWidget(tree)
        return page

    def _system_dictionaries_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        tree = self._tree(["Słownik", "Kod", "Opis"])
        groups = (
            (
                "Typy wyzwalaczy",
                sorted(TRIGGER_TYPES),
                "Kod systemowy — tylko podgląd",
            ),
            (
                "Typy zależności",
                sorted(DEPENDENCY_TYPES),
                "Kod systemowy — tylko podgląd",
            ),
            (
                "Źródła danych",
                ("ESKULAP", "PROGRAM", "RECZNIE"),
                "Źródła techniczne — tylko podgląd",
            ),
            (
                "Statusy synchronizacji",
                ("NOWA", "DOPASOWANA", "POMINIETA", "BLAD"),
                "Projekt słownika — tylko podgląd",
            ),
            (
                "Role systemowe",
                ("ADMIN", "KOORDYNATOR", "KIEROWNIK"),
                "Kody chronione — przypisania w zakładce Role",
            ),
        )
        for group_name, codes, description in groups:
            parent = QTreeWidgetItem(tree, [group_name, "", description])
            for code in codes:
                QTreeWidgetItem(parent, ["", code, description])
        tree.expandAll()
        tree.resizeColumnToContents(0)
        tree.resizeColumnToContents(1)
        layout.addWidget(tree)
        return page

    def _reference_dictionaries_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        tree = self._tree(["Dane referencyjne", "Źródło", "Tryb"])
        for name in (
            "Jednostki organizacyjne",
            "Typy konsultacji",
            "Typy badań",
        ):
            QTreeWidgetItem(
                tree,
                [name, "Eskulap Gateway", "Wyłącznie do odczytu"],
            )
        tree.resizeColumnToContents(0)
        tree.resizeColumnToContents(1)
        layout.addWidget(tree)
        note = QLabel(
            "Dane referencyjne nie są kopiowane do słowników KOMPAS. "
            "Są pobierane z Eskulapa na żądanie."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        return page

    def _dictionaries_tab(self):
        title, description = TAB_DEFINITIONS[0]
        page = self._page(
            title,
            description,
            "Zakładka służy do bezpiecznego podglądu słowników. "
            "Na tym etapie dane nie mogą być tutaj edytowane.",
        )
        groups = QTabWidget()
        groups.addTab(
            self._business_dictionaries_page(),
            "Dane biznesowe",
        )
        groups.addTab(
            self._system_dictionaries_page(),
            "Dane systemowe",
        )
        groups.addTab(
            self._reference_dictionaries_page(),
            "Dane referencyjne Eskulapa",
        )
        page._settings_layout.addWidget(groups, 1)
        self._add_footer(page)
        return page

    @staticmethod
    def _readonly_value(value):
        label = QLabel(str(value))
        label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        label.setWordWrap(True)
        return label

    def _instruction_button(self, label, command, tooltip):
        button = QPushButton(label)
        button.setToolTip(tooltip)
        button.clicked.connect(
            lambda: QMessageBox.information(
                self,
                f"{APP_NAME} — {label}",
                "Test jest dostępny jako skrypt i nie jest uruchamiany "
                "w głównym wątku aplikacji.\n\n"
                f"Uruchom:\n{command}",
            )
        )
        return button

    def _eskulap_integration_tab(self):
        title, description = TAB_DEFINITIONS[1]
        page = self._page(
            title,
            description,
            "Zakładka pokazuje aktywny filtr wizyty kwalifikacyjnej "
            "oraz kontrakty integracyjne. Test Gateway uruchamia się "
            "ręcznie zgodnie z pokazaną instrukcją.",
        )

        qualification_group = QGroupBox(
            "Filtr wizyty kwalifikacyjnej PKK"
        )
        qualification_form = QFormLayout(qualification_group)
        qualification_form.addRow(
            "Pole Eskulapa:",
            self._readonly_value("WP_PARAMETR / PARAMETR_KOD"),
        )
        qualification_form.addRow(
            "Rodzaj wizyty:",
            self._readonly_value(PKK_KWAL_PARAMETR_KOD),
        )
        qualification_form.addRow(
            "Znaczenie:",
            self._readonly_value(
                "F18 — wizyta kwalifikacyjna w PKK"
            ),
        )
        page._settings_layout.addWidget(qualification_group)

        gateway_group = QGroupBox("Test Gateway")
        gateway_layout = QHBoxLayout(gateway_group)
        gateway_layout.addWidget(
            self._instruction_button(
                "Test Gateway",
                "python scripts/test_gateway.py "
                "<nazwisko_lub_PESEL>",
                "Pokaż instrukcję ręcznego testu Eskulap Gateway.",
            )
        )
        gateway_layout.addStretch(1)
        page._settings_layout.addWidget(gateway_group)

        views_group = QGroupBox("Widoki Oracle")
        views_layout = QVBoxLayout(views_group)
        for view_name in (
            "ESK_RAPORTY.V_KOMPAS_PACJENCI",
            "ESK_RAPORTY.V_KOMPAS_WIZYTY",
            "ESK_RAPORTY.V_KOMPAS_PARAMETRY_WIZYT",
            "ESK_RAPORTY.V_KOMPAS_KONSULTACJE",
            "ESK_RAPORTY.V_KOMPAS_BADANIA",
        ):
            views_layout.addWidget(self._readonly_value(view_name))
        page._settings_layout.addWidget(views_group)

        mappings_group = QGroupBox("Mapowania")
        mappings_layout = QFormLayout(mappings_group)
        for label in ("Mapowania badań:", "Mapowania konsultacji:"):
            mappings_layout.addRow(
                label,
                self._readonly_value(PREPARATION_MESSAGE),
            )
        page._settings_layout.addWidget(mappings_group)
        page._settings_layout.addStretch(1)
        self._add_footer(page)
        return page

    def _system_parameters_tab(self):
        title, description = TAB_DEFINITIONS[2]
        page = self._page(
            title,
            description,
            "Zakładka pokazuje aktywną konfigurację bez danych "
            "uwierzytelniających. Hasła nigdy nie są prezentowane.",
        )
        app_config = self._application_config()
        group = QGroupBox("Aktualna konfiguracja")
        form = QFormLayout(group)
        values = (
            ("Tryb bazy KOMPAS:", _readable_engine(self.database_settings)),
            (
                "DSN PostgreSQL:",
                _safe_postgres_dsn(self.database_settings),
            ),
            ("Ścieżka config.ini:", self.config_path),
            (
                "Domyślna liczba miesięcy:",
                app_config.default_months if app_config else "Brak danych",
            ),
            (
                "Domyślna jednostka:",
                app_config.default_jo_id if app_config else "Brak danych",
            ),
            (
                "Długość przedziału:",
                (
                    f"{app_config.slot_minutes} minut"
                    if app_config
                    else "Brak danych"
                ),
            ),
            (
                "Godziny harmonogramu:",
                (
                    f"{app_config.hour_start}:00–"
                    f"{app_config.hour_end}:00"
                    if app_config
                    else "Brak danych"
                ),
            ),
            ("Wersja aplikacji:", f"{VERSION} (build {BUILD})"),
        )
        for label, value in values:
            form.addRow(label, self._readonly_value(value))
        page._settings_layout.addWidget(group, 1)
        self._add_footer(page)
        return page

    def _roles_tab(self):
        title, description = TAB_DEFINITIONS[3]
        page = self._page(
            title,
            description,
            "Administrator może dodawać i edytować użytkowników, "
            "resetować hasła, blokować konta oraz przypisywać role "
            "i jednostki organizacyjne.",
        )
        page._settings_layout.addWidget(
            UsersWindow(self.current_user, page),
            1,
        )
        self._add_footer(page)
        return page

    def _open_directory(self, path, label):
        if not path.exists() or not path.is_dir():
            QMessageBox.information(
                self,
                APP_NAME,
                f"{label} nie istnieje:\n{path}",
            )
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            QMessageBox.warning(
                self,
                APP_NAME,
                f"Nie udało się otworzyć katalogu:\n{path}",
            )

    def _folder_button(self, label, path, tooltip):
        button = QPushButton(label)
        button.setToolTip(tooltip)
        button.clicked.connect(
            lambda: self._open_directory(path, label)
        )
        return button

    def _diagnostics_tab(self):
        title, description = TAB_DEFINITIONS[4]
        page = self._page(
            title,
            description,
            "Testy połączeń są dostępne jako skrypty uruchamiane poza "
            "głównym wątkiem UI. Przyciski pokazują instrukcję.",
        )

        tests_group = QGroupBox("Testy połączeń")
        tests_layout = QHBoxLayout(tests_group)
        tests_layout.addWidget(
            self._instruction_button(
                "Test PostgreSQL",
                "python scripts/test_db_postgres.py",
                "Pokaż instrukcję testu połączenia PostgreSQL.",
            )
        )
        tests_layout.addWidget(
            self._instruction_button(
                "Test Oracle / Gateway",
                "python scripts/test_gateway.py "
                "<nazwisko_lub_PESEL>",
                "Pokaż instrukcję testu Oracle i Eskulap Gateway.",
            )
        )
        tests_layout.addStretch(1)
        page._settings_layout.addWidget(tests_group)

        folders_group = QGroupBox("Katalogi")
        folders_layout = QHBoxLayout(folders_group)
        folders_layout.addWidget(
            self._folder_button(
                "Pokaż katalog logów",
                self.logs_path,
                "Otwórz katalog z logami aplikacji.",
            )
        )
        folders_layout.addWidget(
            self._folder_button(
                "Pokaż katalog aplikacji",
                self.application_dir,
                "Otwórz katalog instalacji aplikacji.",
            )
        )
        folders_layout.addStretch(1)
        page._settings_layout.addWidget(folders_group)
        page._settings_layout.addStretch(1)
        self._add_footer(page)
        return page

    def _system_information_tab(self):
        title, description = TAB_DEFINITIONS[5]
        page = self._page(
            title,
            description,
            "Informacje techniczne są prezentowane wyłącznie do odczytu.",
        )
        group = QGroupBox("Informacje")
        form = QFormLayout(group)
        values = (
            ("Nazwa aplikacji:", APP_NAME),
            ("Wersja:", VERSION),
            ("Build:", BUILD),
            ("Wersja Python:", platform.python_version()),
            ("Tryb bazy:", _readable_engine(self.database_settings)),
            ("Katalog aplikacji:", self.application_dir),
            ("Katalog logów:", self.logs_path),
            ("Ścieżka config.ini:", self.config_path),
        )
        for label, value in values:
            form.addRow(label, self._readonly_value(value))
        page._settings_layout.addWidget(group, 1)
        self._add_footer(page)
        return page


__all__ = [
    "SystemSettingsWindow",
    "TAB_DEFINITIONS",
    "_safe_postgres_dsn",
]
