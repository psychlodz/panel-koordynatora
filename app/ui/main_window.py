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
    QVBoxLayout,
    QWidget,
)

from version import APP_NAME, VERSION


class MainWindow(QMainWindow):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self._windows = {}
        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        self.resize(920, 680)
        self.setMinimumSize(760, 580)

        central_widget = QWidget()
        central_widget.setObjectName("launcherRoot")
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(44, 34, 44, 30)
        layout.setSpacing(20)

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
        buttons.setHorizontalSpacing(18)
        buttons.setVerticalSpacing(18)
        self.schedule_button = QPushButton(
            "Harmonogram pracy\nDostępność zespołu i plan pracy"
        )
        self.programs_button = QPushButton(
            "Programy\nKonfiguracja programów KOMPAS"
        )
        self.pathways_button = QPushButton(
            "Ścieżki\nElementy i przebieg programu"
        )
        self.new_episode_button = QPushButton(
            "Nowy epizod\nRozpoczęcie programu pacjenta"
        )
        self.users_button = QPushButton(
            "Administracja\nUżytkownicy i uprawnienia"
        )
        self.exit_button = QPushButton("Zakończ")

        for button in (
            self.schedule_button,
            self.programs_button,
            self.pathways_button,
            self.new_episode_button,
            self.users_button,
        ):
            button.setProperty("role", "tile")
            button.setCursor(Qt.CursorShape.PointingHandCursor)

        buttons.addWidget(self.schedule_button, 0, 0)
        buttons.addWidget(self.programs_button, 0, 1)
        buttons.addWidget(self.pathways_button, 1, 0)
        buttons.addWidget(self.new_episode_button, 1, 1)
        buttons.addWidget(self.users_button, 2, 0, 1, 2)
        layout.addLayout(buttons)
        layout.addStretch(1)

        self.users_button.setVisible(bool(current_user.is_admin))

        footer = QHBoxLayout()
        footer.addStretch(1)
        self.exit_button.setProperty("role", "secondary")
        self.exit_button.setMinimumWidth(140)
        self.exit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        footer.addWidget(self.exit_button)
        layout.addLayout(footer)

        self.schedule_button.clicked.connect(self.open_schedule)
        self.programs_button.clicked.connect(self.open_programs)
        self.pathways_button.clicked.connect(self.show_pathways_message)
        self.new_episode_button.clicked.connect(self.open_new_episode)
        self.users_button.clicked.connect(self.open_users)
        self.exit_button.clicked.connect(QApplication.instance().quit)

    def _show_window(self, key, factory):
        existing = self._windows.get(key)
        if existing is not None and existing.isVisible():
            existing.raise_()
            existing.activateWindow()
            return
        try:
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

        self._show_window("schedule", factory)

    def open_programs(self):
        def factory():
            from app.ui.programs_window import ProgramsWindow

            return ProgramsWindow()

        self._show_window("programs", factory)

    def show_pathways_message(self):
        QMessageBox.information(
            self,
            APP_NAME,
            "Wybierz program w module Programy.",
        )

    def open_new_episode(self):
        try:
            from app.ui.new_episode_wizard import EpisodeWizard
        except ImportError:
            QMessageBox.information(
                self,
                APP_NAME,
                "Moduł w przygotowaniu",
            )
            return
        self._show_window("new_episode", EpisodeWizard)

    def open_users(self):
        if not self.current_user.is_admin:
            return

        def factory():
            from app.ui.users_window import UsersWindow

            return UsersWindow(self.current_user)

        self._show_window("users", factory)
