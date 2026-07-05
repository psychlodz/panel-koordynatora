import math
from contextlib import contextmanager

from PySide6.QtCore import QEvent, QEventLoop, QPointF, QTimer, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QVBoxLayout,
    QWidget,
)


DEFAULT_MESSAGE = "Trwa pobieranie danych..."
INDICATOR_ATTRIBUTE = "_kompas_busy_indicator"


class SpinnerWidget(QWidget):
    """Animowany wskaźnik zajętości bez sugerowania procentu postępu."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._step = 0
        self.setFixedSize(58, 58)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.timer = QTimer(self)
        self.timer.setInterval(80)
        self.timer.timeout.connect(self._advance)

    def start(self):
        self._step = 0
        self.timer.start()
        self.show()
        self.update()

    def stop(self):
        self.timer.stop()
        self.hide()

    def _advance(self):
        self._step = (self._step + 1) % 12
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = 20
        dot_radius = 4

        for index in range(12):
            distance = (index - self._step) % 12
            color = QColor("#145A8D")
            color.setAlpha(max(38, 255 - distance * 18))
            angle = math.radians(index * 30 - 90)
            point = QPointF(
                center.x() + math.cos(angle) * radius,
                center.y() + math.sin(angle) * radius,
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(point, dot_radius, dot_radius)


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

        self.spinner = SpinnerWidget()
        panel_layout.addWidget(
            self.spinner,
            0,
            Qt.AlignmentFlag.AlignCenter,
        )

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
        self.spinner.start()
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
            self.spinner.stop()
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
