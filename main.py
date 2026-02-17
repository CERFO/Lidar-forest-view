"""
Main entry point: launcher to choose between the navigation tool and the project maker tool.
"""
import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QSurfaceFormat
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from forest_view.logger import setup_logging


def main():
    setup_logging()

    # OpenGL format required by forest_view
    fmt = QSurfaceFormat()
    fmt.setVersion(4, 5)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    QSurfaceFormat.setDefaultFormat(fmt)

    app = QApplication(sys.argv)
    app.setApplicationName("Forest View Launcher")

    dialog = QDialog()
    dialog.setWindowTitle("Choisir l'outil")
    layout = QVBoxLayout(dialog)

    label = QLabel("Que voulez-vous faire ?")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)

    btn_nav = QPushButton("Outil de navigation")
    btn_nav.setMinimumHeight(44)
    btn_nav.clicked.connect(lambda: run_tool(dialog, "navigation"))
    layout.addWidget(btn_nav)

    btn_project = QPushButton("Outil de création de projet")
    btn_project.setMinimumHeight(44)
    btn_project.clicked.connect(lambda: run_tool(dialog, "project_maker"))
    layout.addWidget(btn_project)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
    buttons.rejected.connect(dialog.reject)
    buttons.rejected.connect(app.quit)
    layout.addWidget(buttons)

    dialog.setMinimumWidth(320)
    dialog.exec()

    sys.exit(app.exec() if app.thread() else 0)


def run_tool(dialog, tool: str):
    """Close launcher and schedule tool to start once the event loop is running."""
    dialog.accept()
    dialog.close()
    QTimer.singleShot(0, lambda: _start_tool(tool))


def _start_tool(tool: str):
    app = QApplication.instance()
    if tool == "navigation":
        from forest_view import run
        run(app)
    elif tool == "project_maker":
        from project_maker import ProjectMaker
        ProjectMaker()


if __name__ == "__main__":
    main()
