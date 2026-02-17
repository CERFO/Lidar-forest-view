from PyQt6.QtGui import QSurfaceFormat
from PyQt6.QtWidgets import QApplication

from forest_view.app_manager import AppManager
from forest_view.logger import setup_logging


def run(app=None):
    """Exécutez l'application de navigation (vue arborescente).

    Arguments :
        app : instance QApplication facultative. Si None, une instance est créée et exec() est appelé.
             Si fourni, AppManager est créé et l'appelant est responsable de app.exec().
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
