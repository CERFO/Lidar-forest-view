from PyQt6.QtGui import QSurfaceFormat
from PyQt6.QtWidgets import QApplication

from forest_view.app_manager import AppManager


def run():
    fmt = QSurfaceFormat()
    fmt.setVersion(4, 5)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    QSurfaceFormat.setDefaultFormat(fmt)
    app = QApplication([])
    manager = AppManager()
    app.exec()


if __name__ == '__main__':
    run()
