from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QStyleOptionButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.widgets.busy_indicator import busy_operation
from app.ui.ui_helpers import create_help_button
from version import APP_NAME, VERSION
from app.services.work_context import work_context


class ModuleTileButton(QPushButton):
    def __init__(self, title, description, parent=None):
        super().__init__("", parent)
        self.tile_title = title
        self.tile_description = description
        self.setAccessibleName(title)
        self.setAccessibleDescription(description)

    def paintEvent(self, _event):
        option = QStyleOptionButton()
        self.initStyleOption(option)
        option.text = ""

        painter = QPainter(self)
        self.style().drawControl(
            QStyle.ControlElement.CE_PushButton,
            option,
            painter,
            self,
        )

        content = self.rect().adjusted(22, 12, -22, -12)
        title_font = QFont(self.font())
        title_font.setPointSizeF(13.5)
        title_font.setBold(True)
        description_font = QFont(self.font())
        description_font.setPointSizeF(9.5)
        description_font.setBold(False)
        description_font.setItalic(True)

        painter.setFont(title_font)
        title_metrics = painter.fontMetrics()
        painter.setFont(description_font)
        description_metrics = painter.fontMetrics()
        spacing = 7
        total_height = (
            title_metrics.height()
            + spacing
            + description_metrics.height()
        )
        top = content.top() + max(
            0,
            (content.height() - total_height) // 2,
        )

        if not self.isEnabled():
            color = QColor("#94A3B8")
        elif option.state & QStyle.StateFlag.State_MouseOver:
            color = QColor("#0B426B")
        else:
            color = QColor("#17324A")
        painter.setPen(color)

        painter.setFont(title_font)
        title = title_metrics.elidedText(
            self.tile_title,
            Qt.TextElideMode.ElideRight,
            content.width(),
        )
        painter.drawText(
            QRect(
                content.left(),
                top,
                content.width(),
                title_metrics.height(),
            ),
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter,
            title,
        )

        painter.setFont(description_font)
        description = description_metrics.elidedText(
            self.tile_description,
            Qt.TextElideMode.ElideRight,
            content.width(),
        )
        painter.drawText(
            QRect(
                content.left(),
                top + title_metrics.height() + spacing,
                content.width(),
                description_metrics.height(),
            ),
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter,
            description,
        )


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

        unit_row = QHBoxLayout()
        unit_row.addStretch(1)
        unit_row.addWidget(QLabel("Aktualna jednostka:"))
        self.unit_combo = QComboBox()
        self.unit_combo.setMinimumWidth(420)
        self.unit_combo.setToolTip(
            "Wybierz jednostkę używaną w tej sesji aplikacji."
        )
        for unit in work_context.user_units:
            self.unit_combo.addItem(unit.display_name, unit)
        if work_context.current_unit is not None:
            for index in range(self.unit_combo.count()):
                unit = self.unit_combo.itemData(index)
                if unit.jo_id == work_context.current_unit.jo_id:
                    self.unit_combo.setCurrentIndex(index)
                    break
        if self.unit_combo.count() == 0:
            self.unit_combo.addItem("Brak przypisanej jednostki", None)
            self.unit_combo.setEnabled(False)
        unit_row.addWidget(self.unit_combo)
        unit_row.addStretch(1)
        header_layout.addLayout(unit_row)
        layout.addWidget(header)

        section_title = QLabel("Moduły")
        section_title.setObjectName("sectionTitle")
        layout.addWidget(section_title)

        buttons = QGridLayout()
        buttons.setHorizontalSpacing(16)
        buttons.setVerticalSpacing(16)
        buttons.setColumnStretch(0, 1)
        buttons.setColumnStretch(1, 1)
        self.schedule_button = ModuleTileButton(
            "Harmonogram pracy",
            "Dostępność zespołu i plan pracy",
        )
        self.programs_button = ModuleTileButton(
            "Programy",
            "Konfiguracja programów KOMPAS",
        )
        self.episodes_button = ModuleTileButton(
            "Dashboard epizodów",
            "Stan realizacji programów pacjentów",
        )
        self.qualification_button = ModuleTileButton(
            "Wizyty kwalifikacyjne PKK",
            "Zakładanie epizodów na podstawie Eskulapa",
        )
        self.users_button = ModuleTileButton(
            "Administracja",
            "Ustawienia systemu i uprawnienia",
        )
        self.exit_button = QPushButton("Zakończ")
        self.help_button = create_help_button(
            self,
            "Pulpit główny",
            "To okno służy do uruchamiania modułów KOMPAS.\n\n"
            "Możesz otworzyć harmonogram, programy, epizody, wizyty "
            "kwalifikacyjne oraz — jako administrator — ustawienia "
            "systemu.\n\n"
            "Nie uruchamiaj ponownie modułu, który jest już otwarty.",
        )

        self.schedule_button.setToolTip(
            "Otwórz harmonogram dostępności i planu pracy zespołu."
        )
        self.programs_button.setToolTip(
            "Otwórz listę i konfigurację programów KOMPAS."
        )
        self.episodes_button.setToolTip(
            "Otwórz dashboard realizacji epizodów i zadań."
        )
        self.qualification_button.setToolTip(
            "Pobierz wizyty kwalifikacyjne PKK i przypisz program."
        )
        self.users_button.setToolTip(
            "Otwórz Ustawienia systemu, słowniki i uprawnienia."
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
            button.setMinimumSize(280, 104)

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
        self.users_button.clicked.connect(self.open_system_settings)
        self.exit_button.clicked.connect(QApplication.instance().quit)
        self.unit_combo.currentIndexChanged.connect(
            self._current_unit_changed
        )

    def _current_unit_changed(self, _index):
        unit = self.unit_combo.currentData()
        if unit is not None:
            work_context.set_current_unit(unit)

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
            from app.ui.episodes_dashboard_window import (
                EpisodesDashboardWindow,
            )

            return EpisodesDashboardWindow(
                current_user=self.current_user,
            )

        self._show_window(
            "episodes",
            factory,
            "Trwa otwieranie dashboardu epizodów...",
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

    def open_system_settings(self):
        if not self.current_user.is_admin:
            return

        def factory():
            from app.ui.system_settings_window import (
                SystemSettingsWindow,
            )

            return SystemSettingsWindow(self.current_user)

        self._show_window(
            "system_settings",
            factory,
            "Trwa otwieranie Ustawień systemu...",
        )

    def open_users(self):
        """Zgodność ze starszym wywołaniem modułu administracji."""
        self.open_system_settings()
