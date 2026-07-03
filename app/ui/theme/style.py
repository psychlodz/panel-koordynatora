from PySide6.QtGui import QFont


ACCENT = "#245A8D"
ACCENT_HOVER = "#1D4C79"
ACCENT_PRESSED = "#173D62"


STYLE_SHEET = f"""
QWidget {{
    background-color: #F3F6FA;
    color: #1F2937;
    font-family: "Segoe UI";
    font-size: 10pt;
}}

QMainWindow, QDialog {{
    background-color: #F3F6FA;
}}

QFrame[card="true"] {{
    background-color: #FFFFFF;
    border: 1px solid #DDE5EE;
    border-radius: 14px;
}}

QLabel {{
    background-color: transparent;
}}

QLabel#appTitle {{
    color: #173D62;
    font-size: 30pt;
    font-weight: 700;
}}

QLabel#appSubtitle {{
    color: #536579;
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
    color: #26394D;
    font-size: 13pt;
    font-weight: 600;
    padding-top: 4px;
}}

QPushButton {{
    min-height: 34px;
    padding: 7px 16px;
    color: #FFFFFF;
    background-color: {ACCENT};
    border: 1px solid {ACCENT};
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
    min-height: 92px;
    padding: 18px 22px;
    color: #20364C;
    background-color: #FFFFFF;
    border: 1px solid #D5E0EB;
    border-radius: 12px;
    text-align: left;
    font-size: 14pt;
    font-weight: 600;
}}

QPushButton[role="tile"]:hover {{
    color: {ACCENT};
    background-color: #F8FBFE;
    border: 2px solid #7FA8CB;
}}

QPushButton[role="tile"]:pressed {{
    background-color: #EAF2F9;
    border-color: {ACCENT};
}}

QPushButton[role="secondary"] {{
    color: #334155;
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
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
    color: #1F2937;
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
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

QTableView {{
    color: #263442;
    background-color: #FFFFFF;
    alternate-background-color: #F5F8FB;
    border: 1px solid #D8E1EA;
    border-radius: 7px;
    gridline-color: #E5EBF1;
    selection-color: #17324B;
    selection-background-color: #CFE1F0;
    qproperty-alternatingRowColors: true;
}}

QHeaderView::section {{
    padding: 9px 8px;
    color: #32485D;
    background-color: #EAF0F6;
    border: none;
    border-right: 1px solid #D6E0E9;
    border-bottom: 1px solid #CCD8E3;
    font-weight: 600;
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
    border: 1px solid #D8E1EA;
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
"""


def apply_theme(app):
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(STYLE_SHEET)
