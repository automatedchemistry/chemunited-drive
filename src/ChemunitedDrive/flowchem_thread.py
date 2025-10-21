from PyQt5.QtCore import QProcess, QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QTextBrowser
from datetime import datetime
import psutil
import signal
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

    def start_process(self, config_file: str = "fake.toml"):
        """
        Start a new FlowChem process with the given configuration file.

        Args:
            config_file (str): Path to a FlowChem TOML configuration file. Defaults to "fake.toml".

        Returns:
            bool: True if the process started (or is already running), False otherwise.
        """
        if self.process.state() != QProcess.Running:  # type: ignore[attr-defined]
            try:
                import flowchem

                main = flowchem.__file__.replace("__init__.py", "__main__.py")

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

        - On Unix: sends SIGINT.
        - On Windows: sends CTRL_BREAK_EVENT (requires console group).
        - If the process does not stop within 3 seconds, attempts termination and then kill.
        - Uses QTimer.singleShot to avoid blocking the GUI thread.
        Emits processStopped when finished.
        """

        if self.process.state() != QProcess.Running:  # type: ignore[attr-defined]
            self.__export_text("Process was not running.")
            self.processStopped.emit()
            return

        self.warning.emit("Attempting to stop the process gracefully...")

        pid = self.process.processId()
        if not pid:
            self.warning.emit("Could not retrieve process ID.")
            self.processStopped.emit()
            return

        try:
            process = psutil.Process(pid)

            # Send appropriate interrupt signal
            if sys.platform.startswith("win"):
                self.warning.emit("Sending CTRL_BREAK_EVENT (Windows).")
                process.send_signal(
                    signal.CTRL_BREAK_EVENT
                )  # more reliable than CTRL_C_EVENT
            else:
                self.__export_text("Sending SIGINT (Unix).")
                process.send_signal(signal.SIGINT)

            # Use QTimer to avoid blocking the GUI
            def check_if_finished():
                if self.process.state() == QProcess.NotRunning:  # type: ignore[attr-defined]
                    self.success.emit("Process terminated gracefully.")
                    self.processStopped.emit()
                else:
                    self.warning.emit("Graceful stop failed, forcing termination.")
                    try:
                        process.terminate()
                        process.wait(3)  # give a few seconds
                        if process.is_running():
                            self.warning.emit("Force killing the process.")
                            process.kill()
                    except Exception as e:
                        self.error.emit(
                            "Error during forced termination - details in log"
                        )
                        self.__export_text(f"Error during forced termination: {e}")
                    self.processStopped.emit()

            # Run check in 3 seconds, non-blocking
            # QObject::~QObject: Timers cannot be stopped from another thread
            # This error appear only the gui is launch through the console
            # A deep investigation should be done regarding it!
            # Each QObject has a built-in timer. Qt might use it for internal purposes
            # The part before ": Timers" shows the function which produced this message.
            # In your case, it is a QObject destructor. This suggests that an object is getting
            # deleted in the wrong thread.
            QTimer.singleShot(3000, check_if_finished)

        except Exception as e:
            self.__export_text(f"Error while trying to stop process: {e}")

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

    def __on_process_error(self, error):
        """Handle QProcess errors (e.g., failed to start, crashed)."""
        self.__export_text(f"Process report Error occurred: {error}")

    def __export_text(self, text: str):
        """Format a log message with a timestamp and emit it via messageEmitted."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.messageEmitted.emit(f"[{timestamp}] {text}")
