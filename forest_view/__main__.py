from PyQt6.QtGui import QSurfaceFormat
from PyQt6.QtWidgets import QApplication

from forest_view.app_manager import AppManager
from forest_view.logger import setup_logging


def run(app=None):
    """Run the navigation (forest view) application.

    Args:
        app: Optional QApplication instance. If None, one is created and exec() is called.
             If provided, AppManager is created and the caller is responsible for app.exec().
    """
    setup_logging()
    fmt = QSurfaceFormat()
    fmt.setVersion(4, 5)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    QSurfaceFormat.setDefaultFormat(fmt)
    created_app = app is None
    if app is None:
        app = QApplication([])
    app.setQuitOnLastWindowClosed(True)
    manager = AppManager()
    if created_app:
        app.exec()


if __name__ == '__main__':
    run()
