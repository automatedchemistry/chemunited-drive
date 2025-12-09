"""
Main module to launch the GUI for finding and configuring devices over serial ports or Ethernet.

Classes:
    - GUI: Main GUI class extending DriveGUI to provide device discovery functionalities.

Functions:
    - call_gui_driver: Launches the application.
"""

from .gui import DriveGUI, MessageBoxCustom
from .frames import MessageBoxRequestIP as MessageBoxRequest
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
from serial.tools import list_ports
from loguru import logger
import aioserial


class GUI(DriveGUI):
    """
    Main GUI class that handles device discovery and configuration.

    Methods:
        - onClickedFinder: Trigger device search on serial or Ethernet.
        - addBlockText: Add configuration block to the text editor.
    """

    def onClickedFinder(self):
        """
        Event handler when the 'Find Device' button is clicked.
        Decides whether to search over serial or Ethernet.
        """
        if not super().onClickedFinder():
            return
        if self.component_serial:
            self._find_device_serial()
        else:
            self._find_device_ethernet()

    def _find_device_serial(self):
        """
        Search for devices over serial ports and add their configuration if found.
        """
        configuration = None

        content = """
            The autodiscover includes modules that involve communication over serial ports.
            Unsupported devices could be placed in an unsafe state as a result of the discovery process!
            These modules are *not* guaranteed to be safe!
            Do you want to search for the device?
        """
        confirm = MessageBoxCustom("", content, self)

        if not confirm.exec():
            return  # User canceled

        msg = ""

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))  # type: ignore[attr-defined]

        port_available = [comport.device for comport in list_ports.comports()]
        msg += f"Found the following serial port(s) on the current device: {port_available}\n"

        for serial_port in port_available:
            msg += f"Looking for known devices on {serial_port}...\n"

            try:
                port = aioserial.Serial(serial_port)
                port.close()
            except OSError:
                msg += f"Skipping {serial_port} (cannot be opened: already in use?)\n"
                continue

            if self.component_finder:
                try:
                    if config := self.component_finder(serial_port):
                        configuration = "".join(config)
                        break
                except Exception as e:
                    self.errorInfoBar(
                        title=f"Error in serial port {serial_port}",
                        content=repr(e)
                    )
                    break

            msg += f"No known device found on {serial_port}\n"

        QApplication.restoreOverrideCursor()

        if configuration:
            self.addBlockText(configuration)
            success_msg = """
                The device was found, and the block corresponding to
                its connections has been added to the configuration file.
                Please check the File Window and edit it as needed.
            """
            self.createSuccessInfoBar("Device Found", content=success_msg, duration=-1)
        else:
            self.errorInfoBar(title="Device Not Found", content=msg)

    def _find_device_ethernet(self):
        """
        Search for devices over Ethernet using user-provided source IP and add their configuration if found.
        """
        logger.info("Open window to get IP address.")

        content = """
            Search for known devices on Ethernet and
            generate configuration stubs. The source IP
            for broadcast packets (relevant if multiple
            Ethernet interfaces are available).
        """
        request = MessageBoxRequest(
            subtitle="Find Devices on Ethernet",
            content=content,
            placeholder_text="169.254.*.*",
            parent=self,
        )

        if not request.exec():
            return  # User canceled

        source_ip = request.urlLineEdit.text()

        logger.info("Setting wait cursor while searching.")

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))  # type: ignore[attr-defined]

        if self.component_finder and (etn_conf := self.component_finder(source_ip)):
            QApplication.restoreOverrideCursor()

            configuration = "".join(etn_conf)
            self.addBlockText(configuration)

            success_msg = """
                The device was found, and the block corresponding to
                its connections has been added to the configuration file.
                Please check the File Window and edit it as needed.
            """
            self.createSuccessInfoBar("Device Found", content=success_msg, duration=-1)
        else:
            QApplication.restoreOverrideCursor()
            self.errorInfoBar(
                "Device Not Found",
                "Ensure that the device is connected to the computer or the network via Ethernet.",
            )

    def addBlockText(self, block: str):
        """
        Add a block of configuration text to the text editor.

        Args:
            block (str): The configuration block to add.
        """
        self.TextBrowserFile.append(block)
        self.TextBrowserFile.setReadOnly(False)
