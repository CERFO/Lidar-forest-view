from PyQt6.QtCore import QEvent, Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class InfiniteLoadBar(QWidget):
    """Barre horizontale fine avec un segment qui se déplace en boucle (effet de chargement infini)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 8)
        self._offset = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def showEvent(self, event):
        super().showEvent(event)
        self._timer.start(32)

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def _tick(self):
        self._offset = (self._offset + 0.04) % 1.0
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        w, h = self.width(), self.height()
        track_radius = h // 2
        chunk_width = max(40, w // 3)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Piste (fond)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(60, 60, 60, 200)))
        painter.drawRoundedRect(QRectF(0, 0, w, h), track_radius, track_radius)
        # Segment mobile (boucle infinie)
        x = (w + chunk_width) * self._offset - chunk_width
        painter.setBrush(QBrush(QColor(74, 158, 255)))
        painter.drawRoundedRect(QRectF(x, 0, chunk_width, h), track_radius, track_radius)


class LoadingOverlay(QWidget):
    """Superposition semi-transparente avec message et barre de chargement infinie."""

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

        self._load_bar = InfiniteLoadBar(panel)
        layout.addWidget(self._load_bar, alignment=Qt.AlignmentFlag.AlignCenter)

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

    def dismiss(self):
        """Retire la superposition proprement : désinstalle le filtre d'événements, masque, puis programme la suppression.
        Évite que le parent n'appelle ce widget après sa destruction."""
        if getattr(self, "_dismissed", False):
            return
        self._dismissed = True
        parent = self.parent()
        if parent is not None:
            parent.removeEventFilter(self)
        self.hide()
        self.deleteLater()

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
