![ChemUnited-Drive](https://github.com/automatedchemistry/chemunited-drive/blob/main/docs/chemunited_drive.svg)

# ChemUnited-Drive Application

This application provides a graphical interface to manage, configure, and run FlowChem projects.
It allows users to load project configuration files, discover connected devices, edit settings, and launch the FlowChem server directly from the interface.

## 🚀 **Installation**

To install the package, simply run:

```bash
pip install Chemunited-drive
```

## 🛠️ Install Directly from GitHub

If you prefer to install the latest development version (with the newest updates and experimental features), you can install ChemUnited-Drive directly from the Git repository:

```
pip install git+https://github.com/<your-username>/Chemunited-drive.git
```


## 🧩 Overview

ChemUnited-Drive acts as a friendly GUI for `FlowChem` configurations, and easily integration whit `ChemUnited Orchestration`.
It bridges the gap between device setup and automation, allowing you to:

* Load existing FlowChem project folders.

* View and edit the __configuration_file.toml.

* Discover supported FlowChem devices (serial or Ethernet).

* Start and stop FlowChem servers from the GUI.

* View process logs in real time.

# 🖼️ Application Workflow

### 1. Main Interface

The main window provides four tabs for navigation:

| Tab          | Purpose                                        |
| ------------ | ---------------------------------------------- |
| **FlowChem** | View and edit the configuration file.          |
| **Project**  | Manage and open existing project folders.      |
| **Discover** | Automatically find connected FlowChem devices. |
| **Logging**  | View logs and FlowChem process messages.       |

### 2. Projects View

![ChemUnited-Drive](https://github.com/automatedchemistry/chemunited-drive/blob/main/docs/projects.png)

The Project tab lists all recent FlowChem projects stored in your workspace.

Each card offers:

* ▶️ Run – Load and execute the project’s configuration file.

* 📂 Open Folder – Open the project directory in the system file browser.

### 3. Configuration View

![ChemUnited-Drive](https://github.com/automatedchemistry/chemunited-drive/blob/main/docs/run01.png)

When a project is loaded, its configuration file (__configuration_file.toml) is displayed and can be edited.

Use:

* *Run* → to start the FlowChem server.

* *Stop* → to terminate it.

A progress bar shows the initialization status, and the application provides live feedback and clickable server links once the process is running.

### 4. Run and Monitor FlowChem

![ChemUnited-Drive](https://github.com/automatedchemistry/chemunited-drive/blob/main/docs/run02.png)

When you press Run, the GUI performs the following sequence:

* Saves any edits to a temporary TOML file.

* Asks if you want to terminate existing FlowChem processes.

* Launches FlowChem as a subprocess (flowchem.__main__.py) via QProcess.

* Displays logs and connection information.

Once the server starts (http://127.0.0.1:8000), a direct link appears in the GUI.

Stopping the server gracefully sends a SIGINT or CTRL_BREAK_EVENT, ensuring a clean shutdown.

## ⚙️ Architecture

The project is composed of modular components:

| Module                   | Purpose                                                                                                 |
| ------------------------ | ------------------------------------------------------------------------------------------------------- |
| **`gui.py`**             | Defines the main GUI (`DriveGUI`) and its logic for configuration, running, and process control.        |
| **`frames.py`**          | Contains reusable dialog windows and card widgets (e.g., project cards, IP request dialog).             |
| **`flowchem_thread.py`** | Manages the FlowChem subprocess using `QProcess`, including logging, startup, and graceful termination. |
| **`main.py`**            | Extends the GUI with device discovery logic for serial and Ethernet interfaces.                         |
| **`utils.py`**           | Provides helper functions (e.g., checking server URL, managing temp directories).                       |
| **`__main__.py`**        | Entry point to start the full GUI application.                                                          |

## 🚀 Running the Application

To start the GUI manually, run:

```bash
python -m ChemunitedDrive
```

or, if installed as a package:

```bash
chemunited-drive
```

## 🧠 How It Works Internally

Process Flow

flowchart TD
    A[User loads config file] --> B[Validate TOML]
    B -->|Valid| C[Save temporary config]
    C --> D[Terminate existing FlowChem processes?]
    D --> E[Launch FlowChem process via QProcess]
    E --> F[Monitor stdout/stderr for logs]
    F --> G[Detect "Uvicorn running..." message]
    G --> H[Emit processStart signal]
    H --> I[Show clickable server link in GUI]

Stopping the Server

flowchart TD
    A[User clicks Stop] --> B[Send SIGINT or CTRL_BREAK_EVENT]
    B --> C[Wait 3s for graceful termination]
    C -->|Still running| D[Force terminate or kill process]
    D --> E[Emit processStopped signal]
    E --> F[Update GUI and reset progress bar]

## 🧰 Device Discovery

![ChemUnited-Drive](https://github.com/automatedchemistry/chemunited-drive/blob/main/docs/devices.png)

The Discover tab uses built-in FlowChem finders to detect connected devices:

* Serial devices (via pyserial and aioserial).

* Ethernet devices (via broadcast search using user-defined IP).

Each discovered device automatically appends its configuration block to the current TOML file.

## 🗂️ Temporary Files

All temporary and recent project files are stored in:

`%APPDATA%/ChemUnited/ChemUnited_Recent_Projects`

This includes:

* `__temporary_cfg.toml` – last edited configuration.

* `recent_projects.toml` – list of project paths.

## 🧾 Logging

The application logs:

* QProcess messages from FlowChem.

* Success, warning, and error InfoBars.

* Full traceback details in case of exceptions.

Logs appear both in the Logging tab and in the console (via loguru).

## 🤝 Contributing

Contributions are very welcome!

If you`d like to report bugs, suggest new features, or contribute code improvements, please follow these guidelines:

1 Fork the repository on GitHub.

2 Create a new branch for your feature or fix:

```bash
git checkout -b feature/my-new-feature
```

3 Commit your changes with clear messages:

```bash
git commit -m "Add feature X or fix bug Y"
```

4 Push your branch to your fork:

```bash
git push origin feature/my-new-feature
```

5 Open a Pull Request (PR) in the main repository.

```bash
git push origin feature/my-new-feature
```

Describe clearly what your change does and, if possible, include screenshots or code snippets.

## 🐛 Reporting Issues

If you find a bug or unexpected behavior:

Open the Issues tab in the GitHub repository.

Provide:

* A clear title and short description.

* Steps to reproduce the issue.

* Expected vs. observed behavior.

* (Optional) Screenshots or error logs.

This helps maintainers reproduce and fix the problem quickly.

## ❤️ Join the Project

ChemUnited-Drive is an open collaborative project developed within the
Automation Group – Department of Biomolecular Systems.

We welcome external contributions, bug reports, and ideas for new features.
Your participation helps make FlowChem integration more powerful and accessible.
