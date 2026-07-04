from contextlib import contextmanager

from PySide6.QtCore import QEvent, QEventLoop, Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


DEFAULT_MESSAGE = "Trwa pobieranie danych..."
INDICATOR_ATTRIBUTE = "_kompas_busy_indicator"


class BusyIndicator(QWidget):
    """Nakładka blokująca okno podczas operacji synchronicznej lub wątku."""

    def __init__(self, parent):
        super().__init__(parent)
        self._depth = 0
        self.setObjectName("busyOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        panel = QFrame()
        panel.setObjectName("busyPanel")
        panel.setMinimumWidth(340)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(32, 26, 32, 26)
        panel_layout.setSpacing(14)

        self.message_label = QLabel(DEFAULT_MESSAGE)
        self.message_label.setObjectName("busyMessage")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        panel_layout.addWidget(self.message_label)

        self.progress = QProgressBar()
        self.progress.setObjectName("busyProgress")
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        panel_layout.addWidget(self.progress)

        layout.addWidget(panel)
        parent.installEventFilter(self)
        self.hide()

    def eventFilter(self, watched, event):
        if watched is self.parentWidget() and event.type() in (
            QEvent.Type.Resize,
            QEvent.Type.Show,
        ):
            self.setGeometry(watched.rect())
        return super().eventFilter(watched, event)

    def show_busy(self, message=DEFAULT_MESSAGE):
        self._depth += 1
        self.message_label.setText(message or DEFAULT_MESSAGE)
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents(
            QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
        )

    def hide_busy(self):
        if self._depth == 0:
            return
        self._depth -= 1
        QApplication.restoreOverrideCursor()
        if self._depth == 0:
            self.hide()
            QApplication.processEvents(
                QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
            )


def _indicator(parent):
    indicator = getattr(parent, INDICATOR_ATTRIBUTE, None)
    if indicator is None:
        indicator = BusyIndicator(parent)
        setattr(parent, INDICATOR_ATTRIBUTE, indicator)
    return indicator


def show_busy(message=DEFAULT_MESSAGE, parent=None):
    parent = parent or QApplication.activeWindow()
    if parent is None:
        raise RuntimeError("Brak aktywnego okna dla Busy Indicator")
    indicator = _indicator(parent)
    indicator.show_busy(message)
    return indicator


def hide_busy(parent=None):
    parent = parent or QApplication.activeWindow()
    if parent is None:
        return
    indicator = getattr(parent, INDICATOR_ATTRIBUTE, None)
    if indicator is not None:
        indicator.hide_busy()


@contextmanager
def busy_operation(parent, message=DEFAULT_MESSAGE):
    show_busy(message, parent)
    try:
        yield
    finally:
        hide_busy(parent)
