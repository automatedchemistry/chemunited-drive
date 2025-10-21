from ChemunitedDrive.main import GUI
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
import rich_click as click
import sys


@click.command()
def main():
    """
    Set up the application environment and launch the GUI.
    """
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough  # type: ignore[attr-defined]
    )
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)  # type: ignore[attr-defined]
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)  # type: ignore[attr-defined]
    app = QApplication(sys.argv)

    # show_waiting(2)

    w = GUI()
    w.show()
    app.exec_()


if __name__ == "__main__":
    main()
