import logging
import os
import sys
import hashlib
from datetime import date, datetime, time

import pandas as pd
from calendar_logic import (
    make_slots,
    polish_holidays,
    prepare_df,
    rows_for_cell,
    safe_int,
)
from config import app_dir, load_config
from excel_export import export_table_to_excel
from app.services.schedule_service import ScheduleService
from app.ui.widgets.busy_indicator import busy_operation
from app.services.work_context import initialize_work_context, work_context
from version import APP_NAME, VERSION
from PySide6.QtCore import QDate, QTimer, Qt, QRect, Signal
from PySide6.QtGui import QColor, QBrush, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QSplitter,
    QListWidget,
    QListWidgetItem,
    QCheckBox,
    QMenuBar,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
    QTextEdit,
)


DNI_TYG = {
    0: "pon.",
    1: "wt.",
    2: "śr.",
    3: "czw.",
    4: "pt.",
    5: "sob.",
    6: "niedz.",
}


BASE_DIR = app_dir()
LOG_DIR = os.path.join(BASE_DIR, "logs")
EXPORT_DIR = os.path.join(BASE_DIR, "export")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "plan_pracy.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)


PERSON_COLORS = [
    "#1f5fbf", "#2f7d32", "#a84300", "#7b1fa2",
    "#00838f", "#ad1457", "#5d4037", "#455a64",
    "#3949ab", "#558b2f", "#ef6c00", "#6a1b9a",
    "#00695c", "#c2185b", "#3e2723", "#37474f",
]


class PersonColorDelegate(QStyledItemDelegate):
    """Rysuje nazwiska w komórce różnymi kolorami bez przebudowywania siatki."""

    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter: QPainter, option, index):
        lines = index.data(Qt.UserRole)
        if not lines:
            super().paint(painter, option, index)
            return

        painter.save()

        # tło i zaznaczenie zostawiamy stylowi Qt
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        opt.widget.style().drawControl(QStyle.CE_ItemViewItem, opt, painter, opt.widget)

        rect = option.rect.adjusted(5, 3, -4, -3)
        font = option.font
        font.setPointSize(max(7, font.pointSize()))
        painter.setFont(font)
        fm = painter.fontMetrics()
        line_h = fm.height() + 1
        y = rect.top() + fm.ascent()

        for entry in lines:
            if y > rect.bottom():
                painter.setPen(QColor("#666666"))
                painter.drawText(QRect(rect.left(), y - fm.ascent(), rect.width(), line_h), Qt.AlignLeft, "…")
                break
            text = entry.get("text", "")
            color = entry.get("color", "#202020")
            painter.setPen(QColor(color))
            painter.drawText(QRect(rect.left(), y - fm.ascent(), rect.width(), line_h), Qt.AlignLeft, text)
            y += line_h

        painter.restore()


class PlanPracyApp(QWidget):
    slot_selected = Signal(str, str)

    def __init__(
        self,
        selection_mode=False,
        initial_notes="",
        current_user=None,
    ):
        super().__init__()
        self.selection_mode = selection_mode
        self.initial_notes = initial_notes or ""
        self.current_user = current_user
        self.users_window = None
        self.cfg = load_config()
        self.df_last = pd.DataFrame()
        self.df_view = pd.DataFrame()
        self.visit_availability_calendar = None
        self.current_start = None
        self.current_end = None
        self._updating_filters = False
        self._ready_for_auto_refresh = False
        self.person_color_map: dict[str, str] = {}
        self.schedule_service = ScheduleService()

        self.setWindowTitle(
            f"{APP_NAME} - Harmonogram pracy - wybór terminu"
            if self.selection_mode
            else f"{APP_NAME} - Harmonogram pracy"
        )
        self.resize(1500, 900)

        self.default_jo_id = (
            work_context.current_unit.jo_id
            if work_context.current_unit is not None
            else self.cfg.default_jo_id
        )
        self.default_months = 1
        # Widok zbiorczy: 7:00-22:00, pięć stałych przedziałów po 3 godziny.
        self.slot_minutes = self.cfg.slot_minutes
        self.hour_start = self.cfg.hour_start
        self.hour_end = self.cfg.hour_end

        layout = QVBoxLayout(self)

        if self.current_user and self.current_user.is_admin:
            menu_bar = QMenuBar(self)
            administration_menu = menu_bar.addMenu("Administracja")
            users_action = administration_menu.addAction("Użytkownicy")
            users_action.triggered.connect(self.open_users_window)
            layout.setMenuBar(menu_bar)

        if self.selection_mode:
            selection_hint = QLabel(
                "Tryb planowania zadania: wybierz komórkę dnia i przedziału "
                "godzinowego."
            )
            selection_hint.setObjectName("selectionHint")
            layout.addWidget(selection_hint)

        panel = QHBoxLayout()
        self.jednostka_combo = QComboBox()
        self.jednostka_combo.setMinimumWidth(360)
        self.jednostka_combo.setEditable(False)
        self.jednostka_combo.addItem(f"{self.default_jo_id} — domyślna jednostka", int(self.default_jo_id) if str(self.default_jo_id).isdigit() else self.default_jo_id)

        self.btn_units = QPushButton("Odśwież jednostki")
        self.btn_units.clicked.connect(self.odswiez_jednostki)

        self.data_od = QDateEdit()
        current_date = QDate.currentDate()
        self.data_od.setDate(
            QDate(current_date.year(), current_date.month(), 1)
        )
        self.data_od.setCalendarPopup(True)

        self.miesiace = QSpinBox()
        self.miesiace.setMinimum(1)
        self.miesiace.setMaximum(12)
        self.miesiace.setValue(self.default_months)

        self.btn_load = QPushButton("Odśwież")
        self.btn_load.clicked.connect(self.refresh_active_tab)

        self.btn_export = QPushButton("Eksport do Excel")
        self.btn_export.clicked.connect(self.eksportuj_excel)

        self.btn_close = QPushButton("Zamknij")
        self.btn_close.clicked.connect(self.close)

        unit_label = QLabel("Jednostka:")
        date_label = QLabel("Od:")
        months_label = QLabel("Miesięcy:")
        date_label.setMinimumWidth(72)
        months_label.setMinimumWidth(72)
        date_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )
        months_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        panel.addWidget(unit_label)
        panel.addWidget(self.jednostka_combo)
        panel.addWidget(self.btn_units)
        panel.addWidget(date_label)
        panel.addWidget(self.data_od)
        panel.addWidget(months_label)
        panel.addWidget(self.miesiace)
        panel.addWidget(self.btn_load)
        panel.addWidget(self.btn_export)
        panel.addWidget(self.btn_close)
        layout.addLayout(panel)

        self.info = QLabel("Gotowy")
        layout.addWidget(self.info)

        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self.on_schedule_tab_changed)
        layout.addWidget(self.tabs, 1)

        employee_tab = QWidget()
        employee_layout = QVBoxLayout(employee_tab)
        employee_layout.setContentsMargins(0, 0, 0, 0)
        body = QSplitter(Qt.Horizontal)
        employee_layout.addWidget(body, 1)

        left_panel = QWidget()
        left_panel.setMinimumWidth(260)
        left_panel.setMaximumWidth(360)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)

        title = QLabel("Pracownicy / szybki filtr")
        title.setObjectName("panelTitle")
        left_layout.addWidget(title)

        self.person_search = QLineEdit()
        self.person_search.setPlaceholderText("Szukaj pracownika...")
        self.person_search.textChanged.connect(self.apply_person_search)
        left_layout.addWidget(self.person_search)

        person_buttons = QHBoxLayout()
        self.btn_all_persons = QPushButton("Wszyscy")
        self.btn_all_persons.clicked.connect(self.show_all_persons)
        self.btn_clear_persons = QPushButton("Wyczyść")
        self.btn_clear_persons.clicked.connect(self.clear_person_filters)
        person_buttons.addWidget(self.btn_all_persons)
        person_buttons.addWidget(self.btn_clear_persons)
        left_layout.addLayout(person_buttons)

        self.person_list = QListWidget()
        self.person_list.itemChanged.connect(self.apply_person_filter)
        left_layout.addWidget(self.person_list, 1)

        hint = QLabel("Zaznacz osoby, aby filtrować. Brak zaznaczenia = wszyscy.\nKolor osoby jest stały wg nazwiska.")
        hint.setWordWrap(True)
        hint.setObjectName("secondaryText")
        left_layout.addWidget(hint)

        body.addWidget(left_panel)

        self.table = QTableWidget()
        self.table.setWordWrap(True)
        self.table.setMouseTracking(True)
        self.table.setItemDelegate(PersonColorDelegate(self.table))
        self.table.cellClicked.connect(self.show_cell_details)
        body.addWidget(self.table)
        body.setStretchFactor(0, 0)
        body.setStretchFactor(1, 1)
        self.tabs.addTab(employee_tab, "Kalendarz pracowników")

        availability_tab = QWidget()
        availability_layout = QVBoxLayout(availability_tab)
        availability_layout.setContentsMargins(4, 4, 4, 4)

        availability_filters = QHBoxLayout()
        availability_filters.addWidget(QLabel("Rodzaj wizyty:"))
        self.visit_type_filter = QLineEdit()
        self.visit_type_filter.setPlaceholderText("Filtruj po kodzie lub nazwie...")
        self.visit_type_filter.textChanged.connect(self.redraw_visit_availability)
        availability_filters.addWidget(self.visit_type_filter, 1)

        self.only_available_checkbox = QCheckBox("Tylko rodzaje z dostępnością")
        self.only_available_checkbox.setChecked(True)
        self.only_available_checkbox.toggled.connect(self.zaladuj_dostepnosc_wizyt)
        availability_filters.addWidget(self.only_available_checkbox)
        availability_layout.addLayout(availability_filters)

        availability_tables = QHBoxLayout()
        availability_tables.setContentsMargins(0, 0, 0, 0)
        availability_tables.setSpacing(0)

        self.visit_availability_name_table = QTableWidget()
        self.visit_availability_name_table.setWordWrap(True)
        self.visit_availability_name_table.setMouseTracking(True)
        self.visit_availability_name_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        self.visit_availability_name_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        self.visit_availability_name_table.setFixedWidth(340)

        self.visit_availability_table = QTableWidget()
        self.visit_availability_table.setWordWrap(True)
        self.visit_availability_table.setMouseTracking(True)
        self.visit_availability_table.cellClicked.connect(
            self.show_visit_availability_details
        )
        self.visit_availability_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Interactive
        )
        self.visit_availability_table.verticalScrollBar().valueChanged.connect(
            self.visit_availability_name_table.verticalScrollBar().setValue
        )
        self.visit_availability_name_table.verticalScrollBar().valueChanged.connect(
            self.visit_availability_table.verticalScrollBar().setValue
        )

        availability_tables.addWidget(self.visit_availability_name_table)
        availability_tables.addWidget(self.visit_availability_table, 1)
        availability_layout.addLayout(availability_tables, 1)
        self.tabs.addTab(availability_tab, "Dostępność rodzajów wizyt")

        # Próba pobrania listy jednostek przy starcie. W razie braku połączenia
        # aplikacja nadal pozwala pracować z domyślnym JO_ID z config.ini.
        try:
            self.odswiez_jednostki(show_errors=False)
        except Exception:
            logging.exception("Nie udało się pobrać listy jednostek przy starcie")
        self.data_od.dateChanged.connect(self.on_schedule_filters_changed)
        self.miesiace.valueChanged.connect(self.on_schedule_filters_changed)
        self.jednostka_combo.currentIndexChanged.connect(
            self.on_schedule_filters_changed
        )
        self._ready_for_auto_refresh = True
        if not self.selection_mode:
            QTimer.singleShot(0, self.zaladuj)


    def current_jo_id(self):
        val = self.jednostka_combo.currentData()
        if val is None:
            return safe_int(self.default_jo_id, self.default_jo_id)
        return val

    def selected_date_range(self):
        start = self.data_od.date().toPython()
        months = self.miesiace.value()
        end = (
            pd.Timestamp(start)
            + pd.DateOffset(months=months)
            - pd.DateOffset(days=1)
        ).date()
        return start, end

    def refresh_active_tab(self):
        if getattr(self, "tabs", None) is not None and self.tabs.currentIndex() == 1:
            self.zaladuj_dostepnosc_wizyt()
        else:
            self.zaladuj()

    def on_schedule_tab_changed(self, index):
        if not self._ready_for_auto_refresh or self.selection_mode:
            return
        if index == 1 and self.visit_availability_calendar is None:
            QTimer.singleShot(0, self.zaladuj_dostepnosc_wizyt)
        elif index == 0 and self.df_last.empty:
            QTimer.singleShot(0, self.zaladuj)

    def on_schedule_filters_changed(self, *args):
        if not self._ready_for_auto_refresh or self.selection_mode:
            return
        QTimer.singleShot(0, self.refresh_active_tab)

    def pobierz_jednostki(self) -> pd.DataFrame:
        return self.schedule_service.list_organizational_units()

    def odswiez_jednostki(self, show_errors: bool = True):
        try:
            self.info.setText("Pobieranie listy jednostek...")
            with busy_operation(
                self,
                "Trwa pobieranie listy jednostek z Eskulapa...",
            ):
                df = self.pobierz_jednostki()
            current = str(self.current_jo_id())
            self.jednostka_combo.blockSignals(True)
            self.jednostka_combo.clear()
            selected_idx = 0
            for idx, (_, rec) in enumerate(df.iterrows()):
                jo_id = int(rec["JO_ID"])
                symbol = str(rec.get("JO_SYMBOL") or "").strip()
                nazwa = str(rec.get("JO_NAZWA") or "").strip()
                label = f"{symbol} — {nazwa}  [{jo_id}]" if symbol or nazwa else f"Jednostka [{jo_id}]"
                self.jednostka_combo.addItem(label, jo_id)
                if str(jo_id) == current or str(jo_id) == str(self.default_jo_id):
                    selected_idx = idx
            if self.jednostka_combo.count() == 0:
                self.jednostka_combo.addItem(f"{self.default_jo_id} — domyślna jednostka", int(self.default_jo_id))
            self.jednostka_combo.setCurrentIndex(min(selected_idx, self.jednostka_combo.count() - 1))
            self.jednostka_combo.blockSignals(False)
            self.info.setText(f"Pobrano jednostki: {self.jednostka_combo.count()}.")
        except Exception as exc:
            logging.exception("Błąd pobierania listy jednostek")
            if show_errors:
                QMessageBox.warning(
                    self,
                    "Jednostki",
                    "Nie udało się pobrać listy jednostek z Eskulapa.\n\n"
                    "Szczegóły zapisano w logs\\plan_pracy.log",
                )
            self.info.setText("Nie pobrano listy jednostek")

    def zaladuj_dostepnosc_wizyt(self, *args):
        try:
            jo_id = safe_int(self.current_jo_id(), None)
            if jo_id is None:
                QMessageBox.warning(self, "Błąd", "Nieprawidłowy identyfikator jednostki.")
                return

            start, end = self.selected_date_range()
            self.info.setText("Pobieranie dostępności rodzajów wizyt...")
            with busy_operation(
                self,
                "Pobieranie dostępności rodzajów wizyt z Eskulapa...",
            ):
                self.visit_availability_calendar = (
                    self.schedule_service.get_visit_type_date_range_calendar(
                        jo_id=jo_id,
                        date_from=start,
                        date_to=end,
                        only_available=self.only_available_checkbox.isChecked(),
                    )
                )
                self.redraw_visit_availability()
            rows_count = len(self.visit_availability_calendar.get("rows", []))
            self.info.setText(
                f"Wczytano dostępność rodzajów wizyt: {rows_count} pozycji."
            )
        except Exception:
            logging.exception("Błąd podczas ładowania dostępności rodzajów wizyt")
            QMessageBox.critical(
                self,
                "Błąd",
                "Nie udało się pobrać dostępności rodzajów wizyt z Eskulapa.\n\n"
                "Szczegóły zapisano w logs\\plan_pracy.log",
            )
            self.info.setText("Błąd")

    def availability_day_header(self, day_date: date) -> str:
        return f"{day_date.day:02d}\n{DNI_TYG[day_date.weekday()].upper()}"

    def redraw_visit_availability(self):
        calendar = self.visit_availability_calendar
        table = getattr(self, "visit_availability_table", None)
        name_table = getattr(self, "visit_availability_name_table", None)
        if table is None or name_table is None:
            return
        if not calendar:
            table.clear()
            table.setRowCount(0)
            table.setColumnCount(0)
            name_table.clear()
            name_table.setRowCount(0)
            name_table.setColumnCount(0)
            return

        pattern = self.visit_type_filter.text().strip().casefold()
        rows = [
            row
            for row in calendar.get("rows", [])
            if not pattern
            or pattern in str(row.get("code", "")).casefold()
            or pattern in str(row.get("name", "")).casefold()
        ]
        days = calendar.get("days", [])

        name_table.clear()
        name_table.setRowCount(len(rows))
        name_table.setColumnCount(1)
        name_table.setHorizontalHeaderLabels(["Rodzaj wizyty"])
        name_table.verticalHeader().setVisible(False)

        table.clear()
        table.setRowCount(len(rows))
        table.setColumnCount(len(days))
        table.setHorizontalHeaderLabels(
            [self.availability_day_header(day) for day in days]
        )
        table.verticalHeader().setVisible(False)

        for row_index, row in enumerate(rows):
            name_item = QTableWidgetItem(str(row.get("name", "")))
            name_item.setToolTip(
                f"{row.get('name', '')}\nKod: {row.get('code', '')}"
            )
            name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            name_table.setItem(row_index, 0, name_item)

            for day_index, day_date in enumerate(days):
                cell = row.get("cells", {}).get(day_date, {})
                text = str(cell.get("text", "") or "")
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                item.setToolTip(str(cell.get("tooltip", "") or text))
                item.setData(Qt.UserRole, cell.get("details", []))
                item.setData(
                    Qt.UserRole + 1,
                    {
                        "code": row.get("code"),
                        "name": row.get("name"),
                        "date": day_date,
                    },
                )
                item.setBackground(
                    QBrush(self.cell_base_color(row_index, day_date))
                )
                if not text:
                    item.setForeground(QBrush(QColor(170, 170, 170)))
                table.setItem(row_index, day_index, item)

        name_table.setColumnWidth(0, 320)
        name_table.resizeRowsToContents()
        for column in range(table.columnCount()):
            table.setColumnWidth(column, 96)
        table.resizeRowsToContents()
        for row in range(max(table.rowCount(), name_table.rowCount())):
            table_height = table.rowHeight(row) if row < table.rowCount() else 0
            name_height = (
                name_table.rowHeight(row)
                if row < name_table.rowCount()
                else 0
            )
            height = max(58, min(130, max(table_height, name_height)))
            if row < table.rowCount():
                table.setRowHeight(row, height)
            if row < name_table.rowCount():
                name_table.setRowHeight(row, height)
        name_table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.Stretch,
        )
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.horizontalHeader().setStretchLastSection(False)

    def show_visit_availability_details(self, row: int, col: int):
        item = self.visit_availability_table.item(row, col)
        if item is None:
            return
        details = item.data(Qt.UserRole) or []
        if not details:
            return
        meta = item.data(Qt.UserRole + 1) or {}
        day_date = meta.get("date")
        code = meta.get("code", "")
        name = meta.get("name", "")
        first = details[0] if details else {}
        unit = " — ".join(
            part
            for part in [
                str(first.get("jo_symbol") or "").strip(),
                str(first.get("jo_nazwa") or "").strip(),
            ]
            if part
        )

        dlg = QDialog(self)
        dlg.setWindowTitle("Dostępność rodzaju wizyty")
        dlg.resize(820, 460)
        layout = QVBoxLayout(dlg)
        title = QLabel(
            f"{name} ({code})\n"
            f"Data: {day_date.isoformat() if day_date else ''}\n"
            f"Jednostka: {unit or 'brak danych jednostki'}"
        )
        title.setWordWrap(True)
        layout.addWidget(title)

        tbl = QTableWidget()
        tbl.setColumnCount(3)
        tbl.setHorizontalHeaderLabels(
            ["Pracownik", "Rodzaje wizyt", "Przedział czasowy"]
        )
        tbl.setRowCount(len(details))
        tbl.setWordWrap(True)
        for row_index, detail in enumerate(details):
            values = [
                str(detail.get("pracownik") or ""),
                str(detail.get("rodzaje_wizyt") or ""),
                str(detail.get("przedzial") or ""),
            ]
            for column_index, value in enumerate(values):
                cell_item = QTableWidgetItem(value)
                cell_item.setToolTip(value)
                if column_index == 2:
                    cell_item.setTextAlignment(Qt.AlignCenter)
                else:
                    cell_item.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
                tbl.setItem(row_index, column_index, cell_item)
        tbl.setColumnWidth(0, 240)
        tbl.setColumnWidth(1, 390)
        tbl.setColumnWidth(2, 150)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.resizeRowsToContents()
        layout.addWidget(tbl, 1)

        btn_close = QPushButton("Zamknij")
        btn_close.clicked.connect(dlg.close)
        layout.addWidget(btn_close)
        dlg.exec()

    def pobierz_plan(self, jo_id: int, data_od: str, data_do: str) -> pd.DataFrame:
        logging.info("Pobieranie planu: jo_id=%s, data_od=%s, data_do=%s", jo_id, data_od, data_do)
        return self.schedule_service.get_work_schedule(
            jo_id=jo_id,
            date_from=data_od,
            date_to=data_do,
        )

    def zaladuj(self):
        try:
            jo_id = self.current_jo_id()
            jo_id = safe_int(jo_id, None)
            if jo_id is None:
                QMessageBox.warning(self, "Błąd", "Nieprawidłowy identyfikator jednostki.")
                return

            start = self.data_od.date().toPython()
            months = self.miesiace.value()
            end = pd.Timestamp(start) + pd.DateOffset(months=months) - pd.DateOffset(days=1)

            self.info.setText("Pobieranie danych...")
            with busy_operation(
                self,
                "Pobieranie harmonogramu pracy z Eskulapa...",
            ):
                df = self.pobierz_plan(
                    jo_id,
                    start.strftime("%Y-%m-%d"),
                    end.strftime("%Y-%m-%d"),
                )
                self.df_last = prepare_df(df)
                self.df_view = self.df_last.copy()
                self.current_start = start
                self.current_end = end
                self.update_person_colors(self.df_last)
                self.populate_person_panel(self.df_last)
                self.rysuj_tabele(self.df_view, start, end)
            self.info.setText(f"Wczytano {len(df)} pozycji planu.")
        except Exception as exc:
            logging.exception("Błąd podczas ładowania danych")
            QMessageBox.critical(
                self,
                "Błąd",
                "Nie udało się pobrać lub wyświetlić harmonogramu pracy.\n\n"
                "Szczegóły zapisano w logs\\plan_pracy.log",
            )
            self.info.setText("Błąd")

    def update_person_colors(self, df: pd.DataFrame):
        persons = []
        if not df.empty and "PRACOWNIK" in df.columns:
            persons = sorted([p for p in df["PRACOWNIK"].dropna().unique().tolist() if str(p).strip()])
        self.person_color_map = {}
        for person in persons:
            # Stabilny kolor zależny od nazwy pracownika, a nie od kolejności wczytania.
            digest = hashlib.md5(str(person).encode("utf-8")).hexdigest()
            idx = int(digest[:8], 16) % len(PERSON_COLORS)
            self.person_color_map[person] = PERSON_COLORS[idx]

    def color_for_person(self, person: str) -> str:
        return self.person_color_map.get(person, "#202020")

    def populate_person_panel(self, df: pd.DataFrame):
        self._updating_filters = True
        try:
            self.person_list.clear()
            persons = []
            if not df.empty and "PRACOWNIK" in df.columns:
                persons = sorted([p for p in df["PRACOWNIK"].dropna().unique().tolist() if str(p).strip()])

            for person in persons:
                item = QListWidgetItem(f"■ {person}")
                item.setData(Qt.UserRole, person)
                item.setCheckState(Qt.Unchecked)
                item.setForeground(QBrush(QColor(self.color_for_person(person))))
                item.setToolTip("Zaznacz, aby filtrować harmonogram tej osoby")
                self.person_list.addItem(item)

            self.apply_person_search()
        finally:
            self._updating_filters = False

    def apply_person_search(self):
        pattern = self.person_search.text().strip().lower() if hasattr(self, "person_search") else ""
        for i in range(self.person_list.count()):
            item = self.person_list.item(i)
            person = str(item.data(Qt.UserRole) or "").lower()
            item.setHidden(bool(pattern and pattern not in person))

    def selected_persons(self) -> list[str]:
        result = []
        for i in range(self.person_list.count()):
            item = self.person_list.item(i)
            if item.checkState() == Qt.Checked:
                person = item.data(Qt.UserRole)
                if person and person not in result:
                    result.append(person)
        return result

    def apply_person_filter(self):
        if self._updating_filters or self.df_last.empty or self.current_start is None:
            return
        persons = self.selected_persons()
        if persons:
            self.df_view = self.df_last[self.df_last["PRACOWNIK"].isin(persons)].copy()
            self.info.setText(f"Filtr osób: {', '.join(persons)}. Pozycji: {len(self.df_view)}.")
        else:
            self.df_view = self.df_last.copy()
            self.info.setText(f"Bez filtra osób. Pozycji: {len(self.df_view)}.")
        self.rysuj_tabele(self.df_view, self.current_start, self.current_end)

    def clear_person_filters(self):
        self._updating_filters = True
        try:
            for i in range(self.person_list.count()):
                self.person_list.item(i).setCheckState(Qt.Unchecked)
        finally:
            self._updating_filters = False
        self.apply_person_filter()

    def show_all_persons(self):
        # Synonim czytelny dla użytkownika: odznaczenie wszystkich oznacza widok wszystkich osób.
        self.clear_person_filters()

    def header_for_day(self, d: pd.Timestamp) -> str:
        marker = "\nDZISIAJ" if d.date() == date.today() else ""
        return f"{d.strftime('%Y-%m-%d')}\n{DNI_TYG[d.weekday()]}{marker}"

    def cell_base_color(self, row_idx: int, day_date: date) -> QColor:
        holidays = polish_holidays(day_date.year)
        if day_date == date.today():
            return QColor(231, 246, 232)  # dzisiaj
        if day_date.weekday() >= 5 or day_date in holidays:
            return QColor(245, 238, 230)  # weekend/swieto
        if row_idx % 2 == 0:
            return QColor(250, 250, 250)
        return QColor(242, 246, 250)

    def normal_text_for_cell(self, rows: pd.DataFrame) -> str:
        if rows.empty:
            return ""
        return "\n".join(rows["PRACOWNIK"].dropna().unique())

    def detail_text_for_cell(self, rows: pd.DataFrame) -> str:
        if rows.empty:
            return ""
        rows = rows.sort_values(["PRACOWNIK", "GODZ_OD", "GODZ_DO"])
        return "\n".join(rows["OPIS_PRACY"].dropna().unique())


    def colored_lines_for_cell(self, rows: pd.DataFrame) -> list[dict]:
        """Zwraca linie do kolorowego rysowania komórki przez PersonColorDelegate."""
        if rows.empty:
            return []
        result = []
        # Jedna linia na osobę; w siatce pokazujemy tylko nazwiska, bez godzin.
        rows_sorted = rows.sort_values(["PRACOWNIK", "GODZ_OD", "GODZ_DO"])
        seen = set()
        for _, rec in rows_sorted.iterrows():
            person = str(rec.get("PRACOWNIK") or "[bez pracownika]")
            if person in seen:
                continue
            seen.add(person)
            result.append({
                "text": f"■ {person}",
                "color": self.color_for_person(person),
            })
        return result

    def detail_rows_for_cell(self, rows: pd.DataFrame) -> pd.DataFrame:
        """Dane do popupu: unikalne osoby z przedziałami pracy w danym dniu."""
        if rows.empty:
            return rows
        cols = ["PRACOWNIK", "GODZ_OD", "GODZ_DO"]
        return (
            rows[cols]
            .drop_duplicates()
            .sort_values(["PRACOWNIK", "GODZ_OD", "GODZ_DO"])
            .reset_index(drop=True)
        )

    def detail_visit_type_rows_for_cell(self, rows: pd.DataFrame) -> pd.DataFrame:
        """Dane do popupu: osoby i rodzaje wizyt możliwe w danym planie."""
        if rows.empty:
            return rows
        result = []
        for (person, godz_od, godz_do), group in rows.groupby(
            ["PRACOWNIK", "GODZ_OD", "GODZ_DO"],
            dropna=False,
        ):
            labels = []
            tooltips = []
            seen = set()
            for value in group.get(
                "RODZAJE_WIZYT_NAZWY",
                pd.Series(dtype=str),
            ).dropna():
                text = str(value).strip()
                if not text:
                    continue
                parts = [
                    part.strip()
                    for part in text.replace(";", "\n").splitlines()
                    if part.strip()
                ]
                for part in parts:
                    if part in seen:
                        continue
                    seen.add(part)
                    labels.append(part)
            for value in group.get(
                "RODZAJE_WIZYT_TOOLTIP",
                pd.Series(dtype=str),
            ).dropna():
                tooltip = str(value).strip()
                if tooltip and tooltip not in tooltips:
                    tooltips.append(tooltip)
            if not labels:
                labels = ["Brak określonych rodzajów wizyt"]
            result.append(
                {
                    "PRACOWNIK": str(person or "[bez pracownika]"),
                    "GODZINY": f"{godz_od}–{godz_do}",
                    "RODZAJE_WIZYT": "\n".join(
                        sorted(labels, key=str.casefold)
                    ),
                    "RODZAJE_WIZYT_TOOLTIP": "\n\n".join(tooltips)
                    or "\n".join(sorted(labels, key=str.casefold)),
                }
            )
        return pd.DataFrame(result).sort_values(["PRACOWNIK", "GODZINY"])

    def rysuj_tabele(self, df: pd.DataFrame, start, end):
        dni = pd.date_range(start=start, end=end, freq="D")
        sloty = make_slots()

        self.table.clear()
        self.table.setRowCount(len(sloty))
        self.table.setColumnCount(len(dni))
        self.table.setVerticalHeaderLabels([slot[2] for slot in sloty])
        self.table.setHorizontalHeaderLabels([self.header_for_day(d) for d in dni])

        for col_idx, dzien in enumerate(dni):
            day_date = dzien.date()
            header = self.table.horizontalHeaderItem(col_idx)
            if header and day_date == date.today():
                header.setBackground(QBrush(QColor(204, 235, 207)))
            elif header and (day_date.weekday() >= 5 or day_date in polish_holidays(day_date.year)):
                header.setBackground(QBrush(QColor(235, 224, 214)))

        for row_idx, (slot_start, slot_end, slot_label) in enumerate(sloty):
            for col_idx, dzien in enumerate(dni):
                day_date = dzien.date()
                rows = rows_for_cell(df, day_date, slot_start, slot_end)
                text = self.normal_text_for_cell(rows)

                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignTop | Qt.AlignLeft)
                item.setBackground(QBrush(self.cell_base_color(row_idx, day_date)))
                item.setData(Qt.UserRole, self.colored_lines_for_cell(rows))
                item.setData(Qt.UserRole + 1, day_date.isoformat())
                item.setData(Qt.UserRole + 2, slot_label)
                if rows.empty:
                    item.setForeground(QBrush(QColor(160, 160, 160)))
                else:
                    item.setToolTip("Kliknij, aby otworzyć okno ze szczegółami godzin pracy.")
                self.table.setItem(row_idx, col_idx, item)

        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        for r in range(self.table.rowCount()):
            self.table.setRowHeight(r, max(92, self.table.rowHeight(r)))
        for c in range(self.table.columnCount()):
            self.table.setColumnWidth(c, max(120, min(220, self.table.columnWidth(c))))
        self.table.setAlternatingRowColors(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

    def show_cell_details(self, row: int, col: int):
        if self.current_start is None:
            return
        if self.df_view.empty and not self.selection_mode:
            return

        dni = pd.date_range(start=self.current_start, end=self.current_end, freq="D")
        sloty = make_slots()
        if col >= len(dni) or row >= len(sloty):
            return

        day_date = dni[col].date()
        slot_start, slot_end, slot = sloty[row]
        cell_rows = rows_for_cell(self.df_view, day_date, slot_start, slot_end)
        rows = self.detail_rows_for_cell(cell_rows)
        if self.selection_mode:
            self.select_schedule_slot(day_date, slot_start, slot_end, slot, rows)
            return
        if rows.empty:
            return
        visit_type_rows = self.detail_visit_type_rows_for_cell(cell_rows)

        dlg = QDialog(self)
        dlg.setWindowTitle(f"{APP_NAME} — {day_date.isoformat()} {DNI_TYG[day_date.weekday()]}, godz. {slot}")
        dlg.resize(760, 420)
        layout = QVBoxLayout(dlg)
        title = QLabel(f"{day_date.isoformat()} ({DNI_TYG[day_date.weekday()]}) — osoby pracujące w przedziale obejmującym {slot}")
        layout.addWidget(title)

        tbl = QTableWidget()
        tbl.setColumnCount(3)
        tbl.setHorizontalHeaderLabels(["Pracownik", "Godziny", "Rodzaje wizyt"])
        tbl.setRowCount(len(visit_type_rows))
        tbl.setWordWrap(True)
        for r_idx, (_, rec) in enumerate(visit_type_rows.iterrows()):
            person = str(rec["PRACOWNIK"])
            color = QColor(self.color_for_person(person))
            visit_types = str(rec["RODZAJE_WIZYT"])
            visit_types_tooltip = str(
                rec.get("RODZAJE_WIZYT_TOOLTIP", visit_types)
            )
            vals = [
                person,
                str(rec["GODZINY"]),
                visit_types,
            ]
            for c_idx, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if c_idx == 0:
                    it.setForeground(QBrush(color))
                if c_idx == 2:
                    it.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
                    it.setToolTip(visit_types_tooltip)
                tbl.setItem(r_idx, c_idx, it)
        tbl.resizeColumnsToContents()
        tbl.setColumnWidth(0, max(220, int(tbl.width() * 0.30)))
        tbl.setColumnWidth(1, max(110, int(tbl.width() * 0.15)))
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.resizeRowsToContents()
        layout.addWidget(tbl)

        btn_close = QPushButton("Zamknij")
        btn_close.clicked.connect(dlg.close)
        layout.addWidget(btn_close)
        dlg.exec()

    def open_users_window(self):
        try:
            from app.ui.users_window import UsersWindow

            self.users_window = UsersWindow(self.current_user)
            self.users_window.show()
        except Exception as exc:
            QMessageBox.critical(
                self,
                APP_NAME,
                f"Nie udało się otworzyć administracji użytkownikami:\n\n{exc}",
            )

    def select_schedule_slot(
        self,
        day_date,
        slot_start,
        slot_end,
        slot_label,
        rows,
    ):
        dlg = QDialog(self)
        dlg.setWindowTitle(f"{APP_NAME} — Wybierz termin zadania")
        dlg.resize(560, 420)
        layout = QVBoxLayout(dlg)
        layout.addWidget(
            QLabel(
                f"Termin: {day_date.isoformat()}, godz. {slot_label}"
            )
        )

        people = QTableWidget()
        people.setColumnCount(3)
        people.setHorizontalHeaderLabels(["Pracownik", "Od", "Do"])
        people.setRowCount(len(rows))
        for row_index, (_, record) in enumerate(rows.iterrows()):
            values = [
                record["PRACOWNIK"],
                record["GODZ_OD"],
                record["GODZ_DO"],
            ]
            for column_index, value in enumerate(values):
                people.setItem(
                    row_index,
                    column_index,
                    QTableWidgetItem(str(value)),
                )
        people.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(people)

        layout.addWidget(QLabel("Uwagi do planowania:"))
        notes_edit = QTextEdit()
        notes_edit.setPlainText(self.initial_notes)
        layout.addWidget(notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            "Wybierz termin"
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        planned_at = datetime.combine(
            day_date,
            time(
                hour=slot_start // 60,
                minute=slot_start % 60,
            ),
        ).isoformat(timespec="minutes")
        self.slot_selected.emit(
            planned_at,
            notes_edit.toPlainText().strip(),
        )

    def eksportuj_excel(self):
        export_table_to_excel(self, self.table, EXPORT_DIR)

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(VERSION)
        from app.ui.login_dialog import LoginDialog

        login_dialog = LoginDialog()
        if login_dialog.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
        initialize_work_context(login_dialog.authenticated_user)
        win = PlanPracyApp(
            current_user=login_dialog.authenticated_user,
        )
        win.show()
        sys.exit(app.exec())
    except Exception:
        logging.exception("Błąd krytyczny aplikacji")
        raise
