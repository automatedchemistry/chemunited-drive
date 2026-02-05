from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
    QAction,
)
from PyQt5.QtCore import Qt, pyqtSignal
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    PushButton,
    ToolButton,
    FluentIcon,
    TransparentToolButton,
    IconWidget,
)
from .indicator_button import ServerIndicator, ServerState


class DeviceCard(QFrame):
    """Custom device card based on your annotations."""

    requestStartup = pyqtSignal(str)  # emits device_name

    def __init__(self, parent: QWidget, device_name: str):
        super().__init__(parent=parent)
        self.device_name = device_name
        self.setObjectName("DeviceCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # --- Right: actions + server indicator
        right = QHBoxLayout(self)
        right.setSpacing(8)
        right.setAlignment(Qt.AlignTop)  # type:ignore[attr-defined]

        # Status label
        self.status_label = BodyLabel("-")
        # 1) Italic (and optionally size)
        font = self.status_label.font()
        font.setItalic(True)
        self.status_label.setFont(font)
        # 2) Color (any CSS color works)
        self.status_label.setStyleSheet("color: black;")
        right.addWidget(
            self.status_label, 0, Qt.AlignRight  # type:ignore[attr-defined]
        )

        # Server indicator (clickable)
        self.server_indicator = ServerIndicator(self, diameter=14)
        right.addWidget(self.server_indicator)  # type: ignore[attr-defined]

        self.run_server = TransparentToolButton(FluentIcon.PLAY)
        self.run_server.clicked.connect(self._on_startup)
        self.run_server.setToolTip("Run server - device diagnoses")
        right.addWidget(self.run_server)

    def set_server_state(self, state: ServerState) -> None:
        """Update the server indicator to OFF / STARTING / RUNNING / ERROR."""
        self.server_indicator.set_state(state)

    # --- internal slot
    def _on_startup(self):
        self.requestStartup.emit(self.device_name)

    @classmethod
    def build_card(cls, parent: QWidget, name: str) -> "DeviceCard":
        return cls(parent=parent, device_name=name)


class AssociationCard(QFrame):

    errorIndicator = pyqtSignal(str)  # emits errors

    def __init__(
        self,
        parent: QWidget,
        device_name: str,
        association: dict[str, dict[str, str]],
    ):
        super().__init__(parent)

        self.device_name = device_name
        self.setObjectName("AssociationCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # type:ignore[attr-defined]

        found_any = False

        for abstract_name, component in association.items():
            url = component.get("url", "")
            if not url:
                self.errorIndicator.emit("The association block is missing 'url'")
                continue

            # expected format: "DeviceName/something/something"
            parts = url.split("/")
            url_device = parts[0] if parts else ""
            device_component = parts[-1] if parts else url

            if url_device != device_name:
                continue

            found_any = True
            layout.addWidget(
                self._buildAssociationItem(abstract_name, device_component, url)
            )

        if not found_any:
            # Optional: show a small placeholder instead of an empty card
            layout.addWidget(CaptionLabel(f"No associations for '{device_name}'."))
        else:
            w = QWidget(self)
            v = QVBoxLayout(w)
            v.addWidget(CaptionLabel(""))
            v.addWidget(CaptionLabel("Abstract Component:"))
            v.addWidget(CaptionLabel("Device Component:"))
            layout.insertWidget(0, w)

    def _buildAssociationItem(
        self, abstract_name: str, device_component: str, url: str
    ) -> QWidget:
        w = QWidget(self)
        v = QVBoxLayout(w)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)
        v.setAlignment(Qt.AlignTop)  # type:ignore[attr-defined]

        # Icon widget (THIS is the key)
        icon = IconWidget(FluentIcon.CONNECT, w)
        icon.setFixedSize(18, 18)
        v.addWidget(icon, 0, Qt.AlignHCenter)  # type:ignore[attr-defined]

        title = CaptionLabel(f"{abstract_name}", w)

        subtitle = CaptionLabel(f"{device_component}", w)
        subtitle.setToolTip(url)  # hover to see full url

        v.addWidget(title)
        v.addWidget(subtitle)

        # Optional styling (nice “mini-card” look)
        w.setObjectName("AssociationItem")
        w.setStyleSheet(
            """
            QWidget#AssociationItem {
                border: 1px solid rgba(0,0,0,0.08);
                border-radius: 8px;
            }
        """
        )

        return w
