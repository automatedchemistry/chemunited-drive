from __future__ import annotations

from typing import TYPE_CHECKING, Any
import tomllib
import tomli_w

from ChemunitedDrive.flowchem_thread import FlowchemThread
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel

from qfluentwidgets import (
    GroupHeaderCardWidget,
    CaptionLabel,
    StrongBodyLabel,
    BodyLabel,
    PushButton,
    FluentIcon,
)
from .indicator_button import ServerState
from .device_card import DeviceCard, AssociationCard

if TYPE_CHECKING:
    from ..gui import DriveGUI


def format_args_wrapped(args: dict, max_len: int = 60, sep: str = "  -  ") -> str:
    parts = [f"{k}={v}" for k, v in args.items()]
    lines = []
    cur = ""

    for p in parts:
        candidate = p if not cur else cur + sep + p
        if len(candidate) <= max_len:
            cur = candidate
        else:
            if cur:
                lines.append(cur)
            cur = p  # start new line with this item

    if cur:
        lines.append(cur)

    return "\n".join(lines)


class DeviceCards(GroupHeaderCardWidget):
    """Shows one 'card' per device defined in the TOML configuration."""

    def __init__(self, parent: "DriveGUI"):
        super().__init__(parent)
        self._parent = parent

        self.setTitle("Configuration files devices")
        self.setBorderRadius(8)

        self.button_AddDevice = PushButton("Add New Device")
        self.button_TestAll = PushButton("Test all device")
        self.button_AddDevice.clicked.connect(self.add_device)
        self.button_TestAll.clicked.connect(self.test_all_device)

        widget = QWidget(self)
        layout = QHBoxLayout(widget)
        layout.addWidget(self.button_AddDevice)
        layout.addWidget(self.button_TestAll)
        self.vBoxLayout.addWidget(widget)

        # Keep reference to each device card:
        # {device_name: {"args": dict, "widget": QWidget}}
        self.devices: dict[str, dict[str, Any]] = {}

        self.actual_device: str = ""

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
                content="TOML: 'device' must be a table/dict like: [device] name = {...}",
            )
            self.clear_cards()
            return

        # Rebuild UI
        self.clear_cards()
        content = ""
        for name, args in devices.items():
            if isinstance(args, dict):
                content = format_args_wrapped(args, max_len=30)
            # args is typically a dict with device parameters
            if args is None:
                args = {}
            if not isinstance(args, dict):
                # If someone put a scalar under device.<name>, normalize
                args = {"value": args}

            card = DeviceCard.build_card(parent=self, name=name)
            # connect card requests to your GUI
            card.requestStartup.connect(
                self.open_server_for_device
            )  # implement in DriveGUI
            # Association
            card_assoociation = AssociationCard(
                parent=self,
                device_name=name,
                association=data.get("association", {}),
            )

            group = self.addGroup(
                ":/ChemunitedDrive/chemunited.svg",
                name,
                content,
                widget=card_assoociation,
            )
            # vertical line
            line = QFrame(self)
            line.setFrameShape(QFrame.VLine)
            line.setFrameShadow(QFrame.Sunken)
            line.setFixedWidth(1)  # important
            line.setStyleSheet("background: #d0d0d0;")  # optional (color)
            group.addWidget(line)
            group.addWidget(card)

            self.devices[name] = {"data": devices[name], "widget": group, "card": card}

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
            self._parent.errorInfoBar(title="Config File", content=f"Invalid TOML: {e}")
            return {}

    def add_device(self): ...

    def test_all_device(self): ...

    def open_server_for_device(self, name: str):
        card: DeviceCard = self.devices[name]["card"]
        if card.server_indicator.state in [ServerState.OFF, ServerState.ERROR]:

            if self._parent.flowchemThread.is_running():
                self._parent.warningInfoBar(
                    title="",
                    content="You can only diagnose the device if the server is not running."
                    " Please close the server application before proceeding.",
                    duration=4000,
                )
                return

            self.actual_device = name
            self._parent.freezing_app(True)
            self.set_device_state(name, ServerState.STARTING)

            # Insert the device block to run the server and test it isolated
            complete_text = self._parent.TextBrowserFile.toPlainText()
            self._parent.TextBrowserFile.clear()
            toml_text = tomli_w.dumps({"device": {name: self.devices[name]["data"]}})
            self._parent.TextBrowserFile.setText(toml_text)
            # Run the server
            self._parent.run(ignore_dialog=True)
            # Retrieve the previous file content
            self._parent.TextBrowserFile.clear()
            self._parent.TextBrowserFile.setText(complete_text)
        elif card.server_indicator.state == ServerState.RUNNING:
            # Open the server
            card = self.devices[self.actual_device]["card"]
            card.run_server.setIcon(FluentIcon.PLAY.icon())
            card.run_server.setToolTip("Open the server")
            self.actual_device = ""
            self._parent.stop(ignore_dialog=True)
            self.set_device_state(name, ServerState.NORMAL)
            self._parent.freezing_app(False)

    def set_device_state(self, name: str, state: ServerState):
        card: DeviceCard = self.devices[name]["card"]
        color = state.value.split()[0]
        card.set_server_state(state)
        card.status_label.setText(state.value[len(color) :])
        card.status_label.setStyleSheet(f"color: {color};")

    def start_server(self):
        if self.actual_device:
            self.set_device_state(self.actual_device, ServerState.RUNNING)
            card: DeviceCard = self.devices[self.actual_device]["card"]
            card.run_server.setIcon(FluentIcon.CLOSE.icon())
            card.run_server.setToolTip("Stop")

    def stop_server(self):
        if self.actual_device:
            self.set_device_state(self.actual_device, ServerState.ERROR)
            card: DeviceCard = self.devices[self.actual_device]["card"]
            card.run_server.setIcon(FluentIcon.PLAY.icon())
            card.run_server.setToolTip("Open the server")
            self.actual_device = ""
            self._parent.freezing_app(False)
