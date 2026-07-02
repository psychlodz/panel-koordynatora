import logging
import os
import sys
import hashlib
from datetime import date

import pandas as pd
from calendar_logic import (
    make_slots,
    polish_holidays,
    prepare_df,
    rows_for_cell,
    safe_int,
)
from config import app_dir, load_config
from db import create_connection
from excel_export import export_table_to_excel
from PySide6.QtCore import QDate, Qt, QRect
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
    QVBoxLayout,
    QWidget,
    QDateEdit,
    QDialog,
    QHeaderView,
    QSplitter,
    QListWidget,
    QListWidgetItem,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
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
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.df_last = pd.DataFrame()
        self.df_view = pd.DataFrame()
        self.current_start = None
        self.current_end = None
        self._updating_filters = False
        self.person_color_map: dict[str, str] = {}

        self.setWindowTitle("Plan Pracy v1.0.1")
        self.resize(1500, 900)

        self.default_jo_id = self.cfg.default_jo_id
        self.default_months = self.cfg.default_months
        # Widok zbiorczy: 7:00-22:00, pięć stałych przedziałów po 3 godziny.
        self.slot_minutes = self.cfg.slot_minutes
        self.hour_start = self.cfg.hour_start
        self.hour_end = self.cfg.hour_end
        self.view_name = self.cfg.view_name

        layout = QVBoxLayout(self)

        panel = QHBoxLayout()
        self.jednostka_combo = QComboBox()
        self.jednostka_combo.setMinimumWidth(360)
        self.jednostka_combo.setEditable(False)
        self.jednostka_combo.addItem(f"{self.default_jo_id} — domyślna jednostka", int(self.default_jo_id) if str(self.default_jo_id).isdigit() else self.default_jo_id)

        self.btn_units = QPushButton("Odśwież jednostki")
        self.btn_units.clicked.connect(self.odswiez_jednostki)

        self.data_od = QDateEdit()
        self.data_od.setDate(QDate.currentDate())
        self.data_od.setCalendarPopup(True)

        self.miesiace = QSpinBox()
        self.miesiace.setMinimum(1)
        self.miesiace.setMaximum(12)
        self.miesiace.setValue(self.default_months)

        self.btn_load = QPushButton("Pokaż kalendarz")
        self.btn_load.clicked.connect(self.zaladuj)

        self.btn_export = QPushButton("Eksport do Excel")
        self.btn_export.clicked.connect(self.eksportuj_excel)

        panel.addWidget(QLabel("Jednostka:"))
        panel.addWidget(self.jednostka_combo)
        panel.addWidget(self.btn_units)
        panel.addWidget(QLabel("Od:"))
        panel.addWidget(self.data_od)
        panel.addWidget(QLabel("Miesięcy:"))
        panel.addWidget(self.miesiace)
        panel.addWidget(self.btn_load)
        panel.addWidget(self.btn_export)
        layout.addLayout(panel)

        self.info = QLabel("Gotowy")
        layout.addWidget(self.info)

        body = QSplitter(Qt.Horizontal)
        layout.addWidget(body, 1)

        left_panel = QWidget()
        left_panel.setMinimumWidth(260)
        left_panel.setMaximumWidth(360)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)

        title = QLabel("Pracownicy / szybki filtr")
        title.setStyleSheet("font-weight: bold;")
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
        hint.setStyleSheet("color: #666666; font-size: 10px;")
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

        # Próba pobrania listy jednostek przy starcie. W razie braku połączenia
        # aplikacja nadal pozwala pracować z domyślnym JO_ID z config.ini.
        try:
            self.odswiez_jednostki(show_errors=False)
        except Exception:
            logging.exception("Nie udało się pobrać listy jednostek przy starcie")


    def current_jo_id(self):
        val = self.jednostka_combo.currentData()
        if val is None:
            return safe_int(self.default_jo_id, self.default_jo_id)
        return val

    def pobierz_jednostki(self) -> pd.DataFrame:
        db_user = self.cfg.database_user
        db_password = self.cfg.database_password
        db_dsn = self.cfg.database_dsn
        sql = f"""
            SELECT DISTINCT
                jo_id,
                jo_symbol,
                jo_nazwa
            FROM {self.view_name}
            WHERE jo_id IS NOT NULL
            ORDER BY jo_symbol, jo_nazwa, jo_id
        """
        with create_connection(user=db_user, password=db_password, dsn=db_dsn) as conn:
            return pd.read_sql(sql, conn)

    def odswiez_jednostki(self, show_errors: bool = True):
        try:
            self.info.setText("Pobieranie listy jednostek...")
            QApplication.processEvents()
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
                QMessageBox.warning(self, "Jednostki", f"Nie udało się pobrać listy jednostek:\n\n{exc}")
            self.info.setText("Nie pobrano listy jednostek")

    def pobierz_plan(self, jo_id: int, data_od: str, data_do: str) -> pd.DataFrame:
        db_user = self.cfg.database_user
        db_password = self.cfg.database_password
        db_dsn = self.cfg.database_dsn

        sql = f"""
            SELECT
                data_dnia,
                pracownik,
                godz_od,
                godz_do
            FROM {self.view_name}
            WHERE jo_id = :jo_id
              AND data_dnia BETWEEN TO_DATE(:data_od, 'YYYY-MM-DD')
                                AND TO_DATE(:data_do, 'YYYY-MM-DD')
            ORDER BY data_dnia, godz_od, pracownik
        """

        logging.info("Pobieranie planu: jo_id=%s, data_od=%s, data_do=%s", jo_id, data_od, data_do)
        with create_connection(user=db_user, password=db_password, dsn=db_dsn) as conn:
            return pd.read_sql(sql, conn, params={"jo_id": jo_id, "data_od": data_od, "data_do": data_do})

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
            QApplication.processEvents()

            df = self.pobierz_plan(jo_id, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
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
            QMessageBox.critical(self, "Błąd", f"Nie udało się pobrać lub wyświetlić danych:\n\n{exc}\n\nSzczegóły zapisano w logs\\plan_pracy.log")
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
        if self.df_view.empty or self.current_start is None:
            return

        dni = pd.date_range(start=self.current_start, end=self.current_end, freq="D")
        sloty = make_slots()
        if col >= len(dni) or row >= len(sloty):
            return

        day_date = dni[col].date()
        slot_start, slot_end, slot = sloty[row]
        rows = self.detail_rows_for_cell(rows_for_cell(self.df_view, day_date, slot_start, slot_end))
        if rows.empty:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Plan pracy — {day_date.isoformat()} {DNI_TYG[day_date.weekday()]}, godz. {slot}")
        dlg.resize(560, 360)
        layout = QVBoxLayout(dlg)
        title = QLabel(f"{day_date.isoformat()} ({DNI_TYG[day_date.weekday()]}) — osoby pracujące w przedziale obejmującym {slot}")
        layout.addWidget(title)

        tbl = QTableWidget()
        tbl.setColumnCount(3)
        tbl.setHorizontalHeaderLabels(["Pracownik", "Od", "Do"])
        tbl.setRowCount(len(rows))
        for r_idx, (_, rec) in enumerate(rows.iterrows()):
            person = str(rec["PRACOWNIK"])
            color = QColor(self.color_for_person(person))
            vals = [person, str(rec["GODZ_OD"]), str(rec["GODZ_DO"])]
            for c_idx, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if c_idx == 0:
                    it.setForeground(QBrush(color))
                tbl.setItem(r_idx, c_idx, it)
        tbl.resizeColumnsToContents()
        tbl.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(tbl)

        btn_close = QPushButton("Zamknij")
        btn_close.clicked.connect(dlg.close)
        layout.addWidget(btn_close)
        dlg.exec()

    def eksportuj_excel(self):
        export_table_to_excel(self, self.table, EXPORT_DIR)

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        win = PlanPracyApp()
        win.show()
        sys.exit(app.exec())
    except Exception:
        logging.exception("Błąd krytyczny aplikacji")
        raise
