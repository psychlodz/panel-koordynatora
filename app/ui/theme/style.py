from PySide6.QtGui import QFont


ACCENT = "#145A8D"
ACCENT_HOVER = "#0E4771"
ACCENT_PRESSED = "#093653"
NAVY = "#123B5D"
TEXT = "#111827"


STYLE_SHEET = f"""
QWidget {{
    background-color: #E9EFF5;
    color: {TEXT};
    font-family: "Segoe UI";
    font-size: 10pt;
}}

QMainWindow, QDialog {{
    background-color: #E9EFF5;
}}

QFrame[card="true"] {{
    background-color: #FFFFFF;
    border: 2px solid #B7C5D1;
    border-radius: 14px;
}}

QLabel {{
    background-color: transparent;
}}

QLabel#appTitle {{
    color: {NAVY};
    font-size: 30pt;
    font-weight: 700;
}}

QLabel#appSubtitle {{
    color: #34495E;
    font-size: 12pt;
}}

QLabel#versionBadge {{
    color: {ACCENT};
    background-color: #E8F1F9;
    border: 1px solid #C9DBEC;
    border-radius: 10px;
    padding: 4px 10px;
    font-size: 9pt;
    font-weight: 600;
}}

QLabel#userLabel {{
    color: #64748B;
    font-size: 9pt;
}}

QLabel#sectionTitle {{
    color: #FFFFFF;
    background-color: {NAVY};
    border-radius: 6px;
    font-size: 13pt;
    font-weight: 700;
    padding: 8px 12px;
}}

QPushButton {{
    min-height: 34px;
    padding: 7px 16px;
    color: #FFFFFF;
    background-color: {ACCENT};
    border: 2px solid {ACCENT};
    border-radius: 7px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}

QPushButton:pressed {{
    background-color: {ACCENT_PRESSED};
    border-color: {ACCENT_PRESSED};
}}

QPushButton:disabled {{
    color: #94A3B8;
    background-color: #E2E8F0;
    border-color: #D6DEE8;
}}

QPushButton[role="tile"] {{
    min-height: 88px;
    padding: 18px 22px;
    color: #17324A;
    background-color: #FFFFFF;
    border: 2px solid #A9BAC8;
    border-radius: 12px;
    text-align: left;
    font-size: 14pt;
    font-weight: 600;
}}

QPushButton[role="tile"]:hover {{
    color: #0B426B;
    background-color: #EDF6FC;
    border: 3px solid {ACCENT};
}}

QPushButton[role="tile"]:pressed {{
    background-color: #EAF2F9;
    border-color: {ACCENT};
}}

QPushButton[role="secondary"] {{
    color: #1F3347;
    background-color: #FFFFFF;
    border: 2px solid #8799A8;
}}

QPushButton[role="secondary"]:hover {{
    color: #173D62;
    background-color: #F8FAFC;
    border-color: #8FA8BE;
}}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox,
QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit {{
    min-height: 32px;
    padding: 4px 8px;
    color: {TEXT};
    background-color: #FFFFFF;
    border: 2px solid #A5B4C0;
    border-radius: 6px;
    selection-background-color: #AFCBE2;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QDateEdit:focus, QDateTimeEdit:focus {{
    border: 2px solid #5F91BA;
}}

QComboBox::drop-down {{
    width: 28px;
    border: none;
}}

QTableView, QTableWidget {{
    color: #111827;
    background-color: #FFFFFF;
    alternate-background-color: #EAF1F7;
    border: 2px solid #8FA2B2;
    border-radius: 7px;
    gridline-color: #C3CFD9;
    selection-color: #FFFFFF;
    selection-background-color: #1769A0;
    qproperty-alternatingRowColors: true;
}}

QTableView::item, QTableWidget::item {{
    min-height: 32px;
    padding: 6px 8px;
    border-bottom: 1px solid #D4DDE5;
}}

QTableView::item:selected, QTableWidget::item:selected {{
    color: #FFFFFF;
    background-color: #1769A0;
}}

QHeaderView::section {{
    min-height: 28px;
    padding: 9px 8px;
    color: #FFFFFF;
    background-color: {NAVY};
    border: none;
    border-right: 1px solid #6F879A;
    border-bottom: 2px solid #082D48;
    font-weight: 700;
}}

QTabWidget::pane {{
    background-color: #FFFFFF;
    border: 1px solid #D8E1EA;
    border-radius: 7px;
    top: -1px;
}}

QTabBar::tab {{
    padding: 9px 16px;
    color: #4B6074;
    background-color: #EAF0F6;
    border: 1px solid #D8E1EA;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    color: {ACCENT};
    background-color: #FFFFFF;
    font-weight: 600;
}}

QMenuBar {{
    color: #26394D;
    background-color: #FFFFFF;
    border-bottom: 1px solid #D8E1EA;
    padding: 3px;
}}

QMenuBar::item:selected, QMenu::item:selected {{
    background-color: #DCEAF5;
}}

QMenu {{
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    padding: 5px;
}}

QMenu::item {{
    padding: 7px 24px 7px 12px;
}}

QGroupBox {{
    margin-top: 12px;
    padding-top: 12px;
    border: 2px solid #A5B4C0;
    border-radius: 7px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}}

QToolTip {{
    color: #FFFFFF;
    background-color: #26394D;
    border: 1px solid #172A3C;
    padding: 5px;
}}

QWidget#busyOverlay {{
    background-color: rgba(14, 30, 45, 150);
}}

QFrame#busyPanel {{
    background-color: #FFFFFF;
    border: 2px solid {ACCENT};
    border-radius: 12px;
}}

QLabel#busyMessage {{
    color: {NAVY};
    background-color: transparent;
    font-size: 12pt;
    font-weight: 700;
}}

"""


def apply_theme(app):
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(STYLE_SHEET)
