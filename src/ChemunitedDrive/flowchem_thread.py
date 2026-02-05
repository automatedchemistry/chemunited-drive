from PyQt5.QtCore import QProcess, QObject, pyqtSignal
from PyQt5.QtWidgets import QTextBrowser
from datetime import datetime
import psutil
import sys


class FlowchemThread(QObject):
    """
    A QObject wrapper around QProcess to manage FlowChem processes with logging and signals.

    Features:
        - Start and stop FlowChem as a subprocess using QProcess.
        - Capture and forward stdout/stderr messages to the UI.
        - Emit status signals (success, warning, error, started, stopped).
        - Detect and terminate existing FlowChem processes on the system (via psutil).
        - Cross-platform graceful termination (SIGINT on Unix, CTRL_BREAK_EVENT on Windows).
        - Non-blocking process monitoring using QTimer.
    """

    # Define a signal that carries a string (the log text)
    error = pyqtSignal(str)
    warning = pyqtSignal(str)
    success = pyqtSignal(str)
    messageEmitted = pyqtSignal(str)

    processStart = pyqtSignal()
    processStopped = pyqtSignal()

    def __init__(self, output_text: QTextBrowser | None = None):
        """
        Initialize the FlowchemThread.

        Args:
            output_text (QTextBrowser | None): Optional QTextBrowser widget to send logs to.
        """
        super().__init__()

        # Initialize QProcess
        self.process = QProcess()

        self.output_text = output_text

        # Connect QProcess signals
        self.process.readyReadStandardOutput.connect(self.__on_ready_read_output)
        self.process.readyReadStandardError.connect(self.__on_ready_read_reports)
        self.process.stateChanged.connect(self.__on_state_changed)
        self.process.finished.connect(self.__on_process_finished)
        self.process.errorOccurred.connect(self.__on_process_error)

    def is_running(self):
        return self.process.state() == QProcess.Running  # type: ignore[attr-defined]

    def start_process(self, config_file: str = "fake.toml", virtual_mode: bool = False):
        """
        Start a new FlowChem process with the given configuration file.

        Args:
            config_file (str): Path to a FlowChem TOML configuration file. Defaults to "fake.toml".
            virtual_mode (bool): Virtual Mode.

        Returns:
            bool: True if the process started (or is already running), False otherwise.
        """
        if not self.is_running():
            try:
                if virtual_mode:
                    import flowchem_virtual as server_launch
                else:
                    import flowchem as server_launch

                main = server_launch.__file__.replace("__init__.py", "__main__.py")

                # Start the process
                self.process.start(sys.executable, [str(main), str(config_file)])

                # Update UI
                self.success.emit("Status: Connecting ...")

                return True

            except ImportError:
                self.error.emit("Could not import flowchem module.")
                return False
            except Exception as e:
                self.error.emit("Details in log window.")
                self.__export_text(f"Error: {e}")
                return False
        else:
            self.warning.emit("The process is already running.")
            return True

    def stop_process(self):
        """
        Gracefully stop the running FlowChem process.
        """
        if self.process.state() != QProcess.Running:  # type:ignore[attr-defined]
            self.__export_text("Process was not running.")
            return

        self.warning.emit("Attempting to stop the process gracefully...")

        try:
            # Try to terminate the process using QProcess.terminate()
            self.process.terminate()

            # Wait for the process to finish for up to 3 seconds
            if not self.process.waitForFinished(3000):
                # If it hasn't finished, force kill
                self.warning.emit("Graceful stop failed, forcing termination.")
                self.process.kill()
                if not self.process.waitForFinished(1000):  # Wait a bit more after kill
                    self.error.emit("Process could not be terminated.")
                else:
                    self.success.emit("Process force terminated.")
            else:
                self.success.emit("Process terminated gracefully.")

        except Exception as e:
            self.error.emit(f"Error during process termination: {e}")
            self.__export_text(f"Termination error: {e}")

    def terminate_existing_process(self):
        """
        Detect and terminate any existing FlowChem process running on the system.

        Uses psutil to search for processes containing 'flowchem' and '.toml' in the command line.
        Terminates the first match found.
        """
        # Check if the process is already running
        self.success.emit(
            "Looking for possibles process where flowchem is running in the machine and kill it"
        )
        for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
            if "python" in proc.info["name"]:
                cmd_line = " ".join(proc.info["cmdline"])
                if "flowchem.exe" in cmd_line or (
                    "flowchem" in cmd_line
                    and "__main__.py" in cmd_line
                    and ".toml" in cmd_line
                ):
                    self.success.emit(
                        f"Found existing process: {proc.info['cmdline']}. Terminating..."
                    )
                    proc.terminate()
                    proc.wait()  # Ensure process is terminated
                    self.success.emit("Existing process terminated.")
                    break

    def __on_ready_read_output(self):
        """Handle standard output from the FlowChem process and emit it as a message."""
        output = self.process.readAllStandardOutput().data().decode(errors="replace")
        self.__export_text(f"Process report Output: {output}")

    def __on_ready_read_reports(self):
        """
        Handle standard error (logs/reports) from the FlowChem process.

        Emits processStart when Uvicorn server reports it is ready.
        """
        infor = self.process.readAllStandardError().data().decode(errors="replace")
        self.__export_text(f"Process report: {infor}")
        if "Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)" in infor:
            self.processStart.emit()
        if "AssertionError" in infor:
            self.error.emit(f"AssertionError: {infor.split('AssertionError')[-1]}")
        if "raise" in infor:
            self.error.emit(f"Error: {infor.split('raise')[-1]}")

    def __on_state_changed(self, state):
        """Log and emit when the process state changes (NotRunning, Starting, Running)."""
        if state == QProcess.NotRunning:  # type: ignore[attr-defined]
            self.__export_text("Process is not running.")
        elif state == QProcess.Starting:  # type: ignore[attr-defined]
            self.__export_text("Process is starting.")
        elif state == QProcess.Running:  # type: ignore[attr-defined]
            self.__export_text("Process is running.")

    def __on_process_finished(self, exitCode, exitStatus):
        """Handle process exit and report whether it finished normally or crashed."""
        if exitStatus == QProcess.NormalExit:  # type: ignore[attr-defined]
            self.__export_text(f"Process finished with exit code {exitCode}")
        else:
            self.__export_text(f"Process crashed with exit code {exitCode}")
        self.processStopped.emit()

    def __on_process_error(self, error):
        """Handle QProcess errors (e.g., failed to start, crashed)."""
        self.__export_text(f"Process report Error occurred: {error}")

    def __export_text(self, text: str):
        """Format a log message with a timestamp and emit it via messageEmitted."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.messageEmitted.emit(f"[{timestamp}] {text}")
