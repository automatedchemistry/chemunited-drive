from PyQt5.QtCore import (  # type:ignore[attr-defined]
    Qt,
    pyqtProperty,
    QPropertyAnimation,
    QEasingCurve,
    pyqtSignal,
)
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from enum import StrEnum


class ServerState(StrEnum):
    OFF = "black -"  # no server / unknown
    STARTING = "yellow Initializing ..."  # initializing
    RUNNING = "green Running"  # started
    ERROR = "red Error"  # error
    NORMAL = "green Verified"  # Worked (already test)


class ServerIndicator(QWidget):
    """A small circular indicator with a pulsing halo to show server state."""

    clicked = pyqtSignal()

    def __init__(self, parent=None, diameter: int = 16):
        super().__init__(parent)
        self._diameter = diameter
        self._pulse = 0.0  # 0..1
        self._state = ServerState.OFF

        self._dot_color = QColor("#9aa0a6")  # gray
        self._halo_color = QColor("#9aa0a6")  # gray
        self._halo_enabled = False

        self.setFixedSize(diameter + 14, diameter + 14)
        self.setCursor(Qt.PointingHandCursor)  # type:ignore[attr-defined]

        self._anim = QPropertyAnimation(self, b"pulse", self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(900)
        self._anim.setEasingCurve(QEasingCurve.InOutSine)
        self._anim.setLoopCount(-1)

        self.set_state(ServerState.OFF)

    @property
    def state(self) -> ServerState:
        return self._state

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:  # type:ignore[attr-defined]
            self.clicked.emit()
        super().mousePressEvent(e)

    def set_state(self, state: ServerState):
        self._state = state

        if state == ServerState.OFF:
            self._dot_color = QColor("#9aa0a6")  # gray
            self._halo_color = QColor("#9aa0a6")
            self._halo_enabled = False
            self._anim.stop()
            self.update()
            return

        if state == ServerState.STARTING:
            # Green dot + yellow pulsing halo (your annotation)
            self._dot_color = QColor("#2ecc71")  # green
            self._halo_color = QColor("#f1c40f")  # yellow
            self._halo_enabled = True
            self._anim.start()
            self.update()
            return

        if state == ServerState.RUNNING:
            # Green dot + green pulsing halo (your annotation)
            self._dot_color = QColor("#2ecc71")
            self._halo_color = QColor("#2ecc71")
            self._halo_enabled = True
            self._anim.start()
            self.update()
            return

        if state == ServerState.ERROR:
            # Red dot + red pulsing halo
            self._dot_color = QColor("#e74c3c")
            self._halo_color = QColor("#e74c3c")
            self._halo_enabled = True
            self._anim.start()
            self.update()
            return

        if state == ServerState.NORMAL:
            # Red dot + red pulsing halo
            self._dot_color = QColor("#54a958")
            self._halo_color = QColor("#54a958")
            self._halo_enabled = False
            self._anim.stop()
            self.update()
            return

    def paintEvent(self, event):
        d = self._diameter
        cx = self.width() // 2
        cy = self.height() // 2

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        # Halo: radius grows with pulse, alpha fades
        if self._halo_enabled:
            max_extra = 10
            extra = int(max_extra * self._pulse)
            alpha = int(140 * (1.0 - self._pulse))
            halo = QColor(self._halo_color)
            halo.setAlpha(alpha)

            p.setPen(Qt.NoPen)  # type:ignore[attr-defined]
            p.setBrush(halo)
            p.drawEllipse(
                cx - (d // 2 + extra),
                cy - (d // 2 + extra),
                d + 2 * extra,
                d + 2 * extra,
            )

        # Dot
        p.setPen(Qt.NoPen)  # type:ignore[attr-defined]
        p.setBrush(self._dot_color)
        p.drawEllipse(cx - d // 2, cy - d // 2, d, d)

    def get_pulse(self):
        return self._pulse

    def set_pulse(self, v):
        self._pulse = float(v)
        self.update()

    pulse = pyqtProperty(float, fget=get_pulse, fset=set_pulse)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    gui = ServerIndicator()
    window = QWidget()
    layout = QVBoxLayout(window)
    layout.addWidget(gui)
    gui.set_state(ServerState.STARTING)

    window.show()
    app.exec_()
