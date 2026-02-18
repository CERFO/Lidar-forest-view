from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class LoadingOverlay(QWidget):
    """Superposition semi-transparente avec message et barre de progression indéterminée."""

    def __init__(self, parent: QWidget, message: str = "Chargement…"):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        panel = QFrame(self)
        panel.setObjectName("loadingPanel")
        panel.setStyleSheet(
            "QFrame#loadingPanel {"
            "  background-color: rgba(40, 40, 40, 230);"
            "  border-radius: 8px;"
            "  border: 1px solid rgba(80, 80, 80, 200);"
            "}"
        )

        layout = QVBoxLayout(panel)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        self._label = QLabel(message)
        self._label.setStyleSheet("color: white; font-size: 14px;")
        layout.addWidget(self._label, alignment=Qt.AlignmentFlag.AlignCenter)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setFixedWidth(200)
        self._progress.setStyleSheet(
            "QProgressBar {"
            "  border: 1px solid rgba(100, 100, 100, 200);"
            "  border-radius: 4px;"
            "  background-color: rgba(60, 60, 60, 200);"
            "}"
            "QProgressBar::chunk { background-color: #4a9eff; border-radius: 3px; }"
        )
        layout.addWidget(self._progress, alignment=Qt.AlignmentFlag.AlignCenter)

        self._panel = panel
        self._center_panel()

        parent.installEventFilter(self)

    def _center_panel(self):
        r = self.rect()
        pw = self._panel.sizeHint().width()
        ph = self._panel.sizeHint().height()
        self._panel.setGeometry(
            (r.width() - pw) // 2,
            (r.height() - ph) // 2,
            pw,
            ph,
        )

    def showEvent(self, event):
        super().showEvent(event)
        self.setGeometry(self.parent().rect())
        self._center_panel()
        self.raise_()

    def eventFilter(self, obj, event):
        if obj is self.parent() and event.type() == QEvent.Type.Resize:
            self.setGeometry(self.parent().rect())
            self._center_panel()
        return super().eventFilter(obj, event)

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QColor

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 150))
        super().paintEvent(event)


def show_overlay(parent: QWidget, message: str = "Chargement…") -> LoadingOverlay:
    """Créer, afficher et renvoyer un LoadingOverlay sur le parent. L'appelant doit masquer/supprimer ultérieurement une fois terminé."""
    overlay = LoadingOverlay(parent, message)
    overlay.show()
    return overlay
