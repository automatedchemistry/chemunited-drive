"""
Main GUI module for Flowchem Device Association.

This module provides the main application window for loading, editing, saving,
and managing FlowChem device configuration files.

Classes:
    - DriveGUI: Main application window.
    - BaseInterface: Widget for showing connected devices.
    - LoggingInterface: Widget for showing logs.
    - AutoDiscoverInterface: Widget for device auto-discovery.
    - ConfigurationFileInterface: Widget for editing configuration files.
    - SettingsCard: Card widget showing device information.
    - MessageBoxCustom: Customized confirmation dialog.

Dependencies:
    - PyQt5
    - qfluentwidgets
    - flowchem
    - loguru
    - toml
    - re
    - os
"""

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QListWidgetItem,
)
from PyQt5.QtCore import QUrl, Qt, QTimer, pyqtSlot, QProcess

from qfluentwidgets import (
    PushButton,
    FluentIcon,
    MSFluentWindow,
    TextBrowser,
    InfoBarPosition,
    InfoBar,
    StrongBodyLabel,
    setTheme,
    Theme,
    Dialog,
    ProgressBar,
    HyperlinkLabel,
    ListWidget,
    CommandBarView,
    Flyout,
    Action,
    FlyoutAnimationType,
    InfoBarIcon,
    PrimaryPushButton,
)

from flowchem.utils import device_finder
from flowchem.devices.list_known_device_type import (
    autodiscover_first_party as flowchem_devices_implemented,
)
from .flowchem_thread import FlowchemThread
from .utils import is_url_accessible, TEMPORARY_FILES_FOLDER
from .frames import (
    MessageBoxCustom,
    LoggingInterface,
    AutoDiscoverInterface,
    ConfigurationFileInterface,
    ProjectCardsInterface,
    FileCard,
)

# Python 3.11+: tomllib is built-in. For 3.10 or earlier: pip install tomli
try:
    import tomllib  # 3.11+
except ModuleNotFoundError:  # 3.10 or earlier
    import tomli as tomllib  # type:ignore[no-redef]

from typing import Callable, Optional, Any
from loguru import logger
from pathlib import Path
import inspect
import traceback
import toml
import re
import os


# List all functions in the device_finder module
FUNCTIONS_DEVICE_FINDER = {
    name: func for name, func in inspect.getmembers(device_finder, inspect.isfunction)
}


class DriveGUI(MSFluentWindow):
    """
    Main application window for managing Flowchem device configuration.

    Responsibilities:
    - Load and Save configuration files.
    - Display devices, components, logs, discovery options.
    - Start/stop Flowchem processes.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # use dark theme mode
        setTheme(Theme.LIGHT)  # Use light theme

        self.link = HyperlinkLabel(parent=self)

        # Add Configuration Interface widgets
        self.labelConfFile = StrongBodyLabel("-")
        self.labelMessage = StrongBodyLabel("-")
        self.link = HyperlinkLabel()
        self.TextBrowserFile = TextBrowser(self)
        self.progressBar = ProgressBar(self)
        self.buttonRun = PushButton("Run")
        self.buttonRun.clicked.connect(self.run)
        self.buttonClose = PrimaryPushButton("Stop")
        self.buttonClose.clicked.connect(self.stop)
        self.FileCard = FileCard(self)

        self.LoggingInterface = LoggingInterface(self)
        self.AutoDiscoverInterface = AutoDiscoverInterface(self)
        self.ConfigurationFileInterface = ConfigurationFileInterface(self)
        self.ProjectCardsInterface = ProjectCardsInterface(self)

        self.flowchemThread = FlowchemThread()
        self.progressTimer = QTimer(self)
        self.progressTimer.timeout.connect(self.update_progress)
        self.progress_value = 0

        self.dir_connectivity: str
        self.configuration: dict

        # Add interfaces to navigation
        self._setup_navigation()

        # Setup main widgets
        self._setup_widgets()

        # Setup attributes
        self._initialize_attributes()

        # User can write the configuration file
        self.TextBrowserFile.setReadOnly(False)

        # Flags
        self._running = False
        self.buttonRun.setHidden(False)
        self.buttonClose.setHidden(True)
        self.buttonClose.setStyleSheet(
            """
                PrimaryPushButton {
                    background-color: #E81123;
                    color: white;
                    border-radius: 6px;
                    padding: 6px 12px;
                }
                PrimaryPushButton:hover {
                    background-color: #F1707A;
                }
                PrimaryPushButton:pressed {
                    background-color: #C50F1F;
                }
            """
        )

    def _setup_navigation(self):
        """Setup sidebar navigation."""
        self.addSubInterface(
            interface=self.ConfigurationFileInterface,
            icon=QIcon(":/ChemunitedDrive/flowchem.svg"),
            text="Flowchem",
            isTransparent=True,
        )

        self.addSubInterface(
            interface=self.ProjectCardsInterface,
            icon=QIcon(":/ChemunitedDrive/chemunited.svg"),
            text="Project",
            isTransparent=True,
        )

        self.navigationInterface.addItem(
            routeKey="saveFile",
            icon=FluentIcon.SAVE,
            text="Save",
            onClick=self.save,
            selectable=False,
        )

        self.addSubInterface(
            self.AutoDiscoverInterface,
            FluentIcon.SEARCH,
            "Discover",
            FluentIcon.SEARCH,
            isTransparent=True,
        )

        self.addSubInterface(
            self.LoggingInterface,
            FluentIcon.CODE,
            "Logging",
            FluentIcon.CODE,
            isTransparent=True,
        )

    def _setup_widgets(self):
        """Setup widgets in the window."""
        self.resize(880, 760)
        self.setWindowTitle(
            "ChemUnited-Drive - API Devices Drive Communication through Flowchem"
        )
        self.setWindowIcon(QIcon(":/ChemunitedDrive/flowchem_logo.svg"))
        self.titleBar.raise_()

        # Add Logging Interface widgets
        self.TextBrowser = TextBrowser(self)
        self.LoggingInterface.vBoxLayout.addWidget(self.TextBrowser)

        self.ConfigurationFileInterface.vBoxLayout.addWidget(self.labelConfFile)
        self.ConfigurationFileInterface.vBoxLayout.addWidget(self.labelMessage)
        self.ConfigurationFileInterface.vBoxLayout.addWidget(self.link)
        self.ConfigurationFileInterface.vBoxLayout.addWidget(self.TextBrowserFile)
        self.ConfigurationFileInterface.vBoxLayout.addWidget(self.progressBar)
        self.ConfigurationFileInterface.vBoxLayout.addWidget(self.buttonRun)
        self.ConfigurationFileInterface.vBoxLayout.addWidget(self.buttonClose)

        # Add AutoDiscover Interface widget
        self.listDeviceImplemented = ListWidget(self)
        self.AutoDiscoverInterface.vBoxLayout.addWidget(self.listDeviceImplemented)

        # Add File Cards
        self.ProjectCardsInterface.vBoxLayout.addWidget(self.FileCard)

        self._fillUp_list()

        self._fill_project_cards()

    def _initialize_attributes(self):
        """Initialize internal attributes."""
        self.dir_connectivity = ""
        self.configuration = {}
        self.temporary = os.path.join(TEMPORARY_FILES_FOLDER, "__temporary_cfg.toml")
        self.urlFile = os.path.join(TEMPORARY_FILES_FOLDER, "__temporaryURL.toml")
        self.devices_flowchem: list[str] = []
        self._itemClickedDevicesList: str = ""
        self.component_finder: Optional[Callable] = None
        self.component_serial: bool = False

        ### Connect the signals
        self.flowchemThread.success.connect(self.__success)
        self.flowchemThread.warning.connect(self.__warning)
        self.flowchemThread.error.connect(self.__error)
        self.flowchemThread.messageEmitted.connect(self.__message)
        self.flowchemThread.processStart.connect(self.show_url)
        self.flowchemThread.processStopped.connect(self.__finalize_process)

    @pyqtSlot()
    def show_url(self):
        try:
            # Try loading the configuration file
            self.configuration = toml.load(self.temporary)
        except Exception as error:
            self.handleErros(error, title="The edited file has an issue!")
            return

        dataURL = ""
        response: dict[str, dict[str, Any]]
        device = next(iter(self.configuration["device"].keys()))
        status, response = is_url_accessible(url=f"http://127.0.0.1:8000/{device}/")
        if status:
            first_key = next(iter(response["components"]))
            url = response["components"][first_key]
            dataURL = url.split("8000")[0] + "8000/"

        self.labelMessage.setText("Flowchem server is running successfully")
        self.link.setText(f"Open server - {dataURL}")
        self.link.setUrl(dataURL)
        self._running = True
        self.buttonRun.setHidden(True)
        self.buttonClose.setHidden(False)
        self.progressTimer.stop()
        self.progress_value = 100
        self.progressBar.setValue(self.progress_value)
        self.progressBar.setCustomBarColor(light="#7CB342", dark="#7CB342")

    def update_text(self):
        """
        Update the ConfigurationFileInterface window with the current configuration file content.
        """
        self.labelConfFile.setText(self.dir_connectivity)
        formatted_text = toml.dumps(self.configuration)
        self.TextBrowserFile.setText(formatted_text)

    def save(self):
        """
        Save the current configuration to a TOML file.

        Read the current text from a TextBrowser, parse as TOML, return a dict.
        Make sure the widget contains *plain text* TOML (use setPlainText when setting it).
        """
        raw = (
            self.TextBrowserFile.toPlainText()
        )  # ensures we get plain TOML, even if the browser renders rich text
        try:
            data = tomllib.loads(raw)
        except tomllib.TOMLDecodeError as e:
            # Build a friendly error message with line/column if available
            line = getattr(e, "lineno", None)
            col = getattr(e, "colno", None)

            # tomllib exposes .pos instead of (lineno, colno); compute them if needed
            if line is None and hasattr(e, "pos"):
                pos = getattr(e, "pos", 0)
                before = raw[:pos]
                line = before.count("\n") + 1
                last_nl = before.rfind("\n")
                col = pos + 1 if last_nl == -1 else pos - last_nl

            # final message
            details = str(getattr(e, "msg", e))  # tomli has .msg; fallback to str(e)
            where = (
                f" (line {line}, col {col})"
                if line is not None and col is not None
                else ""
            )
            self.errorInfoBar(title="TOML parse error", content=f"{details}{where}")
            return

        self.configuration = data

        if not self.configuration:
            self.errorInfoBar(
                title="No File", content="There is no configuration to save!"
            )
            return

        try:
            with open(self.dir_connectivity, "w") as f:
                toml.dump(self.configuration, f)
            self.createSuccessInfoBar(
                title="File Saved",
                content=f"Configuration saved to: {self.dir_connectivity}",
            )

        except Exception as e:
            self.errorInfoBar(
                title="Save Error",
                content=f"An error occurred while saving the file: {str(e)}",
            )

    def run(self):
        """
        Execute the FlowChem run sequence.

        - Validate and save the edited configuration file.
        - Ask whether to terminate any existing FlowChem processes.
        - Start a new FlowChem process with the saved configuration.
        - Update device cards with the new device list.
        """
        self.progressBar.setCustomBarColor(light="#90CAF9", dark="#90CAF9")
        self.progressTimer.start(100)

        # Get edited content from the text editor
        edited_content = self.TextBrowserFile.toPlainText()

        # Validate the edited content as TOML
        try:
            toml_data = toml.loads(edited_content)
            with open(self.temporary, "w") as file:
                toml.dump(toml_data, file)
        except Exception as error:
            self.handleErros(error, title="Edited file has an issue!")
            self.progressTimer.stop()
            self.progress_value = 0
            self.progressBar.setValue(self.progress_value)
            return

        # Ask user whether to terminate running FlowChem processes
        content = """
            Do you want to check for any running FlowChem processes on this machine
            and terminate them before starting a new one?
        """
        w = MessageBoxCustom("", content, self)

        if w.exec():
            self.flowchemThread.terminate_existing_process()

        # Start the new FlowChem process
        self.flowchemThread.start_process(config_file=self.temporary)

    def stop(self):
        content = """
                    Are you sure you want to stop the server?
                    Any running FlowChem processes will be terminated.
                """

        w = Dialog("Close Server", content, self)

        if w.exec():
            if self.flowchemThread.process.state() == QProcess.Running:  # type: ignore[attr-defined]
                self.flowchemThread.stop_process()

    @pyqtSlot()
    def __finalize_process(self):
        self.createSuccessInfoBar(
            title="Server Close", content="Server was close successfully"
        )
        self.link.setUrl("")
        self.link.setText("")
        self.labelMessage.setText("No server running")
        self._running = False
        self.buttonRun.setHidden(False)
        self.buttonClose.setHidden(True)
        self.progress_value = 0
        self.progressBar.setValue(self.progress_value)
        self.progressBar.setCustomBarColor(light="#90CAF9", dark="#90CAF9")

    def _fillUp_list(self):
        """
        Populate the AutoDiscoverInterface list with implemented FlowChem devices.
        """
        self.devices_flowchem = list(flowchem_devices_implemented().keys())

        for device in self.devices_flowchem:
            if not device.startswith("Virtual"):
                item = QListWidgetItem(device)
                self.listDeviceImplemented.addItem(item)

        # Connect device selection to event handler
        self.listDeviceImplemented.itemClicked.connect(self.clickedListDevice)

    def _fill_project_cards(self):
        recent = Path(TEMPORARY_FILES_FOLDER) / "recent_projects.toml"
        if recent.is_file():
            recent_dict = toml.load(recent)
            for name, file in recent_dict.items():
                self.FileCard.add_card(Path(file))

    def load_project_config_file(self, file: Path):
        conf = file.parent / "__configuration_file.toml"
        if conf.is_file():
            try:
                # Load and store configuration
                self.configuration = toml.load(conf)
            except Exception as error:
                self.handleErros(
                    error, title=f"There is something wrong with the file '{conf}'!"
                )
                return
            self.dir_connectivity = str(conf)
            self.update_text()
            self.createSuccessInfoBar(
                title="File Loaded",
                content=f"The file '{conf}' was successfully opened. Check the 'File' tab.",
            )

    def clickedListDevice(self):
        """
        Handle the event when a device is clicked in the AutoDiscoverInterface.

        Attempts to find a corresponding finder function for the selected device.
        Shows either a command bar for discovery, or a message with a link to documentation.
        """
        # Store clicked item text
        self._itemClickedDevicesList = self.listDeviceImplemented.currentItem().text()

        # Prepare potential finder function keys
        keys = [
            self._itemClickedDevicesList.lower(),
            re.findall(r"[A-Z][a-z]*", self._itemClickedDevicesList)[0].lower(),
        ]

        hasDeviceFinder = False

        for key in keys:
            if f"{key}_finder" in FUNCTIONS_DEVICE_FINDER:
                self.component_finder = FUNCTIONS_DEVICE_FINDER[f"{key}_finder"]
                self.component_serial = (
                    self.component_finder in device_finder.SERIAL_DEVICE_INSPECTORS
                )
                hasDeviceFinder = True
                break

        if hasDeviceFinder:
            self.showCommandBar()  # Allow discovery if supported
        else:
            # Inform user finder not available
            content = f"""
                Finder function for {self._itemClickedDevicesList} is not implemented,
                due to complexity or safety concerns.
                You can manually create configuration files using the documentation:
            """

            link = HyperlinkLabel(
                QUrl(
                    "https://flowchem.readthedocs.io/en/latest/user-guides/reference/devices/supported_devices.html"
                ),
                "Documentation",
                self,
            )

            w = InfoBar(
                icon=InfoBarIcon.INFORMATION,
                title="Finder Not Implemented",
                content=content,
                orient=Qt.Vertical,  # type: ignore[attr-defined]
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000,
                parent=self,
            )
            w.addWidget(link)
            w.show()

            self.component_finder = None
            self.component_serial = False

    def showCommandBar(self):
        """
        Show a command bar with available actions, specifically to trigger device discovery.
        """
        view = CommandBarView(self)

        action = Action(FluentIcon.SEARCH_MIRROR, "Finder")
        action.triggered.connect(self.onClickedFinder)  # Connect to discovery handler
        view.addAction(action)
        view.resizeToSuitableWidth()

        Flyout.make(view, self.AutoDiscoverInterface, self, FlyoutAnimationType.FADE_IN)

    def onClickedFinder(self):
        if self._running:
            self.warningInfoBar(
                title="Process is running",
                content="Please stop the server before looking for new devices",
            )
            return False
        return True

    def handleErros(self, error, title: str = ""):
        """
        Log and display detailed error information.

        Args:
            error: Exception object to handle.
            title: Title for the error InfoBar.
        """
        error_type = type(error).__name__
        error_message = str(error)
        error_traceback = traceback.format_exc()

        logger.error(
            f"Type: {error_type}\nMessage: {error_message}\n\n{error_traceback}"
        )

        detailed_message = f"Type: {error_type}\nMessage: {error_message}\n\n"

        self.errorInfoBar(title=title, content=detailed_message, duration=-1)

    def errorInfoBar(
        self,
        title: str = "Error",
        content: str = "...",
        is_closable: bool = True,
        duration: int = -1,
    ):
        """
        Display an error InfoBar message at the bottom right of the window.

        Args:
            title: Title for the InfoBar.
            content: Main message content.
            is_closable: Whether the InfoBar can be closed manually.
            duration: Display duration (-1 means permanent).
        """
        logger.error(f"{title} - {content}")
        InfoBar.error(
            title=title,
            content=content,
            orient=Qt.Horizontal,  # type: ignore[attr-defined]
            isClosable=is_closable,
            position=InfoBarPosition.BOTTOM_RIGHT,
            duration=duration,
            parent=self,
        )
        self.TextBrowser.append(f"Logg - title: {title}, content: {content}")
        self.TextBrowser.ensureCursorVisible()  # Scroll to the most recent lin

    def createSuccessInfoBar(self, title: str, content: str, duration=2000):
        """
        Display a success InfoBar message at the top of the window.

        Args:
            title: Title for the InfoBar.
            content: Main message content.
            duration: Display duration in milliseconds.
        """
        logger.info(f"{title} - {content}")
        InfoBar.success(
            title=title,
            content=content,
            orient=Qt.Horizontal,  # type: ignore[attr-defined]
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=duration,
            parent=self,
        )
        self.TextBrowser.append(f"Logg - title: {title}, content: {content}")
        self.TextBrowser.ensureCursorVisible()  # Scroll to the most recent lin

    def warningInfoBar(self, title: str, content: str, duration=2000):
        """
        Display a warning InfoBar message at the top of the window.

        Args:
            title: Title for the InfoBar.
            content: Main message content.
            duration: Display duration in milliseconds.
        """
        logger.warning(f"{title} - {content}")
        InfoBar.warning(
            title=title,
            content=content,
            orient=Qt.Horizontal,  # type: ignore[attr-defined]
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=duration,
            parent=self,
        )
        self.TextBrowser.append(f"Logg - title: {title}, content: {content}")
        self.TextBrowser.ensureCursorVisible()  # Scroll to the most recent lin

    def update_progress(self, step=2, count=40):
        self.progress_value += 1
        self.progressBar.setValue(self.progress_value * step)
        if self.progress_value >= count:
            self.progressTimer.stop()

    @pyqtSlot(str)
    def __success(self, message):
        self.createSuccessInfoBar(title="Flowchem Information", content=message)

    @pyqtSlot(str)
    def __warning(self, message):
        self.warningInfoBar(title="Flowchem Information", content=message)

    @pyqtSlot(str)
    def __error(self, message):
        self.errorInfoBar(title="Flowchem Information", content=message)

    @pyqtSlot(str)
    def __message(self, message):
        self.TextBrowser.append(message)
        self.TextBrowser.ensureCursorVisible()  # Scroll to the most recent lin

    def closeEvent(self, event):
        """
        Override the close event to confirm user intention.

        Warns about:
            - Unsaved configuration changes
            - Termination of running FlowChem processes
        Deletes temporary files on confirmed exit.
        """
        if self._running:
            self.warningInfoBar(
                title="Process is running",
                content="Please stop the server before leave the application",
            )
            event.ignore()
        else:
            # If not running → safe to close immediately
            if os.path.isfile(self.temporary):
                os.remove(self.temporary)
            if os.path.isfile(self.urlFile):
                os.remove(self.urlFile)
            event.accept()
