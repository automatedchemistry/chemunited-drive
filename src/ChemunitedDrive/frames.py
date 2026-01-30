from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget
from qframelesswindow import FramelessDialog
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl, Qt, pyqtSignal
from typing import Any

from qfluentwidgets import (
    GroupHeaderCardWidget,
    ScrollArea,
    Dialog,
    StrongBodyLabel,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    FluentIcon,
    TransparentToolButton,
    SegmentedWidget,
)
from functools import partial
from pathlib import Path


class MessageBoxCustom(Dialog):
    """
    A simple custom confirmation dialog with 'Yes' and 'No' buttons.
    """

    def __init__(self, title: str, content: str, parent=None):
        super().__init__(title, content, parent)
        self.yesButton.setText("Yes")
        self.cancelButton.setText("No")


class MessageBoxRequestIP(FramelessDialog):

    def __init__(
        self,
        subtitle: str,
        content: str,
        placeholder_text: str,
        parent=None,
    ):
        super().__init__(parent=parent)

        self.topLayout: QVBoxLayout
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.Dialog)  # type: ignore[attr-defined]
        self.setAttribute(Qt.WA_TranslucentBackground)  # type: ignore[attr-defined]

        self.setStyleSheet(
            """
            QWidget#TopSection {
                background-color: white;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }
            QWidget#BottomSection {
                background-color: #f2f2f2;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }
        """
        )

        self.initUI()

        # Title
        self.label_title = StrongBodyLabel(subtitle, self)
        self.topLayout.addWidget(self.label_title)

        # Content
        self.label = StrongBodyLabel(content, self)
        self.topLayout.addWidget(self.label)

        # Input Field
        self.urlLineEdit = LineEdit(self)
        self.urlLineEdit.setPlaceholderText(placeholder_text)
        self.topLayout.addWidget(self.urlLineEdit)

    def initUI(self):
        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)

        # Top white section
        self.topWidget = QWidget(self)
        self.topWidget.setObjectName("TopSection")
        self.topLayout = QVBoxLayout(self.topWidget)
        self.topLayout.setContentsMargins(16, 16, 16, 8)

        # Bottom gray section
        bottomWidget = QWidget(self)
        bottomWidget.setObjectName("BottomSection")
        bottomLayout = QHBoxLayout(bottomWidget)
        bottomWidget.setFixedHeight(60)
        bottomLayout.setContentsMargins(16, 0, 16, 0)
        bottomLayout.setSpacing(10)

        self.proceedBtn = PrimaryPushButton("Proceed", self)
        self.cancelBtn = PushButton("Cancel", self)
        bottomLayout.addWidget(self.proceedBtn)
        bottomLayout.addWidget(self.cancelBtn)

        mainLayout.addWidget(self.topWidget)
        mainLayout.addWidget(bottomWidget)

        # Connect buttons
        self.cancelBtn.clicked.connect(self.reject)
        self.proceedBtn.clicked.connect(self.accept)


class SegmentWindow(QWidget):
    switchFrame = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)

        self.pivot = SegmentedWidget(self)
        self.stackedWidget = QStackedWidget(self)
        self.vBoxLayout = QVBoxLayout(self)

        self.vBoxLayout.addWidget(self.pivot)
        self.vBoxLayout.addWidget(self.stackedWidget)
        self.vBoxLayout.setContentsMargins(10, 10, 10, 10)

        self.pivot.currentItemChanged.connect(
            lambda k: self.switchTo(self.findChild(QWidget, k))
        )

    def addSubInterface(
        self, widget: QWidget, objectName: str, text, icon: str, onClick: Any = None
    ):
        widget.setObjectName(objectName)
        self.stackedWidget.addWidget(widget)
        self.pivot.addItem(routeKey=objectName, text=text, icon=icon, onClick=onClick)

    def switchTo(self, widget: QWidget):
        self.stackedWidget.setCurrentWidget(widget)
        self.switchFrame.emit(widget.objectName())


class FileCard(GroupHeaderCardWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self._parent = parent
        self.setTitle("Chemunited Recent Projects")
        self.setBorderRadius(8)

        # keep reference to each file card group
        self.files: dict[str, dict] = {}  # {stem: {"file": Path, "widget": QWidget}}

    def add_card(self, file: Path):
        if file.stem in self.files:
            return

        widget = QWidget()
        layout = QHBoxLayout(widget)

        # Action buttons

        btn_open = TransparentToolButton(FluentIcon.PLAY)
        if hasattr(self._parent, "load_project_config_file"):
            btn_open.clicked.connect(
                partial(self._parent.load_project_config_file, file)
            )
        btn_open.setToolTip("Open Project Configuration File")

        btn_view = TransparentToolButton(FluentIcon.FOLDER)
        btn_view.clicked.connect(partial(self.__view_folder, file.parent))
        btn_view.setToolTip("Open Local File")

        layout.addWidget(btn_open)
        layout.addWidget(btn_view)

        # Add group to card widget
        group = self.addGroup(
            ":/ChemunitedDrive/chemunited.svg",
            f"{file.name}",
            f"{file.stem}",
            widget=widget,
        )

        # store reference
        self.files[file.stem] = {"file": file, "group": group}

    def __view_folder(self, file: Path):
        """Open the file in the OS default program"""
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(file)))


class BaseInterface(ScrollArea):
    """Widget for showing available devices."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setObjectName("BaseInterface")
        self.vBoxLayout.setSpacing(10)
        self.vBoxLayout.setContentsMargins(0, 0, 10, 30)
        self.enableTransparentBackground()


class LoggingInterface(BaseInterface):
    """Widget for displaying log messages."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LoggingInterface")


class AutoDiscoverInterface(BaseInterface):
    """Widget for device autodiscovery functionality."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AutoDiscoverInterface")


class ConfigurationFileInterface(BaseInterface):
    """Widget for editing and saving the configuration file."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ConfigurationFileInterface")


class ProjectCardsInterface(BaseInterface):
    """Widget for access chamunited projects."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ProjectCardsInterface")


class SettingsInterface(BaseInterface):
    """Widget for access settings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsInterface")


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt
    import sys

    # Set high DPI settings for better display scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough  # type: ignore[attr-defined]
    )
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)  # type: ignore[attr-defined]
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)  # type: ignore[attr-defined]

    app = QApplication(sys.argv)

    gui = SegmentWindow(None)
    gui.addSubInterface(
        widget=QWidget(), objectName="A", text="ko", icon=FluentIcon.PLAY
    )
    gui.addSubInterface(
        widget=QWidget(), objectName="B", text="fr", icon=FluentIcon.FOLDER
    )
    gui.show()
    app.exec_()
