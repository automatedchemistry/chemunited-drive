from __future__ import annotations

from typing import TYPE_CHECKING, Any
import tomllib

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel

from qfluentwidgets import GroupHeaderCardWidget, CaptionLabel, StrongBodyLabel, BodyLabel

if TYPE_CHECKING:
    from ..gui import DriveGUI


class DeviceCards(GroupHeaderCardWidget):
    """Shows one 'card' per device defined in the TOML configuration."""

    def __init__(self, parent: "DriveGUI"):
        super().__init__(parent)
        self._parent = parent

        self.setTitle("Configuration files devices")
        self.setBorderRadius(8)

        # Keep reference to each device card:
        # {device_name: {"args": dict, "widget": QWidget}}
        self.devices: dict[str, dict[str, Any]] = {}

    # -------------------------
    # Public API
    # -------------------------
    def update_cards(self) -> None:
        """Delete all current cards and rebuild from the TOML text in TextBrowser."""
        data = self._read_toml_from_parent()
        devices = data.get("device", {})
        if not isinstance(devices, dict):
            # If your TOML has a different shape, you can adapt here
            self._parent.errorInfoBar(
                title="Config File",
                content="TOML: 'device' must be a table/dict like: [device] name = {...}"
            )
            self.clear_cards()
            return

        # Rebuild UI
        self.clear_cards()

        for name, args in devices.items():
            # args is typically a dict with device parameters
            if args is None:
                args = {}
            if not isinstance(args, dict):
                # If someone put a scalar under device.<name>, normalize
                args = {"value": args}

            card = self._build_device_card(name, args)
            group = self.addGroup(
                ":/ChemunitedDrive/chemunited.svg",
                name,
                "content",
                widget=card,
            )
            self.devices[name] = {"args": args, "widget": group}

    def clear_cards(self) -> None:
        """Remove and delete all device card widgets."""
        # Remove widgets we added before
        for info in self.devices.values():
            w = info.get("widget")
            if isinstance(w, QWidget):
                w.setParent(None)
                w.deleteLater()
        self.devices.clear()

    # -------------------------
    # Internal helpers
    # -------------------------
    def _read_toml_from_parent(self) -> dict:
        """Parse TOML from the parent's TextBrowser."""
        text = self._parent.TextBrowserFile.toPlainText()

        try:
            return tomllib.loads(text)
        except Exception as e:
            # Replace with InfoBar / MessageBox in your GUI if you want
            self._parent.errorInfoBar(
                title="Config File",
                content=f"Invalid TOML: {e}"
            )
            return {}

    def _build_device_card(self, name: str, args: dict) -> QWidget:
        """Create one card widget showing a device name and key/value args."""
        card = QFrame(self)
        card.setObjectName("deviceCard")
        card.setFrameShape(QFrame.NoFrame)

        # Layout
        root = QVBoxLayout(card)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        # Header row
        header = QHBoxLayout()
        header.setSpacing(10)

        title = StrongBodyLabel(name, card)
        title.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # Optional: show a "type" field if present
        dev_type = args.get("type") or args.get("kind") or args.get("driver")
        subtitle = CaptionLabel(str(dev_type) if dev_type is not None else "", card)
        subtitle.setTextInteractionFlags(Qt.TextSelectableByMouse)
        subtitle.setVisible(bool(subtitle.text().strip()))

        header.addWidget(title, 1)
        header.addWidget(subtitle, 0, Qt.AlignRight)

        root.addLayout(header)

        # Body: show parameters (excluding the type-like key if you want)
        params_layout = QVBoxLayout()
        params_layout.setSpacing(2)

        hidden_keys = {"type", "kind", "driver"}
        shown = 0

        for k, v in args.items():
            if k in hidden_keys:
                continue
            line = BodyLabel(f"{k}: {v}", card)
            line.setTextInteractionFlags(Qt.TextSelectableByMouse)
            params_layout.addWidget(line)
            shown += 1

        if shown == 0:
            params_layout.addWidget(BodyLabel("No parameters.", card))

        root.addLayout(params_layout)

        # Simple "card" styling (works well with QFluent theme)
        card.setStyleSheet("""
            QFrame#deviceCard {
                border: 1px solid rgba(120, 120, 120, 60);
                border-radius: 8px;
                background: rgba(255, 255, 255, 6);
            }
        """)

        return card
