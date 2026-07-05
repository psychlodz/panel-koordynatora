import sys
from pathlib import Path

from PySide6.QtGui import QFont


PALETTE = {
    "PRIMARY": "#145A8D",
    "PRIMARY_HOVER": "#0E4771",
    "PRIMARY_PRESSED": "#093653",
    "SECONDARY": "#5D7185",
    "SUCCESS": "#238636",
    "WARNING": "#D97706",
    "DANGER": "#C62828",
    "INFO": "#168AAD",
    "BACKGROUND": "#E9EFF5",
    "SURFACE": "#FFFFFF",
    "SURFACE_ALT": "#F4F7FA",
    "TEXT_PRIMARY": "#111827",
    "TEXT_SECONDARY": "#526777",
    "BORDER": "#8FA2B2",
    "SELECTION": "#145A8D",
    "SELECTION_TEXT": "#FFFFFF",
    "STATUS_OVERDUE": "#C62828",
    "STATUS_TO_PLAN": "#F2994A",
    "STATUS_PLANNED": "#2F80ED",
    "STATUS_IN_PROGRESS": "#1BA39C",
    "STATUS_COMPLETED": "#27AE60",
    "STATUS_CANCELLED": "#828282",
}


def style_path() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    project_root = (
        Path(frozen_root)
        if frozen_root
        else Path(__file__).resolve().parents[3]
    )
    return project_root / "resources" / "styles" / "kompas.qss"


def load_style_sheet() -> str:
    path = style_path()
    if not path.exists():
        raise FileNotFoundError(
            f"Nie znaleziono centralnego arkusza stylów: {path}"
        )
    style_sheet = path.read_text(encoding="utf-8")
    for name, color in PALETTE.items():
        style_sheet = style_sheet.replace(f"${{{name}}}", color)
    return style_sheet


def apply_theme(app):
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(load_style_sheet())


__all__ = ["PALETTE", "apply_theme", "load_style_sheet", "style_path"]
