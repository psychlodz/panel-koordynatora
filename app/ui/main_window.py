from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.ui.widgets.busy_indicator import busy_operation
from app.ui.ui_helpers import create_help_button
from version import APP_NAME, VERSION


class MainWindow(QMainWindow):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self._windows = {}
        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        self.resize(920, 680)
        self.setMinimumSize(720, 540)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.setCentralWidget(scroll_area)
        central_widget = QWidget()
        central_widget.setObjectName("launcherRoot")
        scroll_area.setWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(32, 26, 32, 24)
        layout.setSpacing(16)

        header = QFrame()
        header.setProperty("card", True)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(32, 26, 32, 24)
        header_layout.setSpacing(8)

        title_row = QHBoxLayout()
        title = QLabel(APP_NAME)
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label = QLabel(VERSION)
        version_label.setObjectName("versionBadge")
        title_row.addStretch(1)
        title_row.addWidget(title)
        title_row.addWidget(version_label)
        title_row.addStretch(1)
        header_layout.addLayout(title_row)

        subtitle = QLabel(
            "Platforma Koordynacji Programów "
            "Diagnostyczno-Terapeutycznych"
        )
        subtitle.setObjectName("appSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        header_layout.addWidget(subtitle)

        user_label = QLabel(
            f"Zalogowano: {current_user.full_name} ({current_user.login})"
        )
        user_label.setObjectName("userLabel")
        user_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(user_label)
        layout.addWidget(header)

        section_title = QLabel("Moduły")
        section_title.setObjectName("sectionTitle")
        layout.addWidget(section_title)

        buttons = QGridLayout()
        buttons.setHorizontalSpacing(16)
        buttons.setVerticalSpacing(16)
        buttons.setColumnStretch(0, 1)
        buttons.setColumnStretch(1, 1)
        self.schedule_button = QPushButton(
            "Harmonogram pracy\nDostępność zespołu i plan pracy"
        )
        self.programs_button = QPushButton(
            "Programy\nKonfiguracja programów KOMPAS"
        )
        self.episodes_button = QPushButton(
            "Pacjenci w programach\nEpizody i postęp realizacji"
        )
        self.qualification_button = QPushButton(
            "Wizyty kwalifikacyjne PKK\n"
            "Zakładanie epizodów na podstawie Eskulapa"
        )
        self.users_button = QPushButton(
            "Administracja\nUżytkownicy i uprawnienia"
        )
        self.exit_button = QPushButton("Zakończ")
        self.help_button = create_help_button(
            self,
            "Pulpit główny",
            "To okno służy do uruchamiania modułów KOMPAS.\n\n"
            "Możesz otworzyć harmonogram, programy, epizody, wizyty "
            "kwalifikacyjne oraz — jako administrator — użytkowników.\n\n"
            "Nie uruchamiaj ponownie modułu, który jest już otwarty.",
        )

        self.schedule_button.setToolTip(
            "Otwórz harmonogram dostępności i planu pracy zespołu."
        )
        self.programs_button.setToolTip(
            "Otwórz listę i konfigurację programów KOMPAS."
        )
        self.episodes_button.setToolTip(
            "Otwórz listę pacjentów uczestniczących w programach."
        )
        self.qualification_button.setToolTip(
            "Pobierz wizyty kwalifikacyjne PKK i przypisz program."
        )
        self.users_button.setToolTip(
            "Otwórz administrację użytkownikami i rolami."
        )
        self.exit_button.setToolTip("Zamknij aplikację KOMPAS.")

        for button in (
            self.schedule_button,
            self.programs_button,
            self.episodes_button,
            self.qualification_button,
            self.users_button,
        ):
            button.setProperty("role", "tile")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding,
            )
            button.setMinimumSize(280, 96)

        buttons.addWidget(self.schedule_button, 0, 0)
        buttons.addWidget(self.programs_button, 0, 1)
        buttons.addWidget(self.episodes_button, 1, 0)
        buttons.addWidget(self.qualification_button, 1, 1)
        buttons.addWidget(self.users_button, 2, 0)
        buttons.setRowStretch(0, 1)
        buttons.setRowStretch(1, 1)
        buttons.setRowStretch(2, 1 if current_user.is_admin else 0)
        layout.addLayout(buttons, 1)

        self.users_button.setVisible(bool(current_user.is_admin))

        footer = QHBoxLayout()
        footer.addWidget(self.help_button)
        footer.addStretch(1)
        self.exit_button.setProperty("role", "secondary")
        self.exit_button.setMinimumWidth(140)
        self.exit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        footer.addWidget(self.exit_button)
        layout.addLayout(footer)

        self.schedule_button.clicked.connect(self.open_schedule)
        self.programs_button.clicked.connect(self.open_programs)
        self.episodes_button.clicked.connect(self.open_episodes)
        self.qualification_button.clicked.connect(
            self.open_qualification_visits
        )
        self.users_button.clicked.connect(self.open_users)
        self.exit_button.clicked.connect(QApplication.instance().quit)

    def _show_window(self, key, factory, busy_message):
        existing = self._windows.get(key)
        if existing is not None and existing.isVisible():
            existing.raise_()
            existing.activateWindow()
            return
        try:
            with busy_operation(self, busy_message):
                window = factory()
            self._windows[key] = window
            window.show()
        except Exception as exc:
            QMessageBox.critical(
                self,
                APP_NAME,
                f"Nie udało się otworzyć modułu:\n\n{exc}",
            )

    def open_schedule(self):
        def factory():
            from plan_pracy import PlanPracyApp

            return PlanPracyApp(current_user=self.current_user)

        self._show_window(
            "schedule",
            factory,
            "Trwa uruchamianie harmonogramu...",
        )

    def open_programs(self):
        def factory():
            from app.ui.programs_window import ProgramsWindow

            return ProgramsWindow()

        self._show_window(
            "programs",
            factory,
            "Trwa otwieranie listy programów...",
        )

    def open_episodes(self):
        def factory():
            from app.ui.episodes_window import EpisodesWindow

            return EpisodesWindow()

        self._show_window(
            "episodes",
            factory,
            "Trwa otwieranie listy epizodów...",
        )

    def open_qualification_visits(self):
        def factory():
            from app.ui.qualification_visits_window import (
                QualificationVisitsWindow,
            )

            return QualificationVisitsWindow()

        self._show_window(
            "qualification_visits",
            factory,
            "Trwa pobieranie wizyt kwalifikacyjnych...",
        )

    def open_users(self):
        if not self.current_user.is_admin:
            return

        def factory():
            from app.ui.users_window import UsersWindow

            return UsersWindow(self.current_user)

        self._show_window(
            "users",
            factory,
            "Trwa otwieranie administracji...",
        )
