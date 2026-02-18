import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsTextItem,
    QStyle,
)


class PhotoPoint(QGraphicsEllipseItem):
    """
    Point interactif pour les photos sur la carte.

    Paramètres:
        path (str): Chemin de l'image associée.
        x, y (float): Position dans la scène.
        z (float): Altitude.
        yaw, pitch, roll (float): Orientation en degrés.
        parent: CustomMapWidget (pour émettre les signaux).
        size (int): Taille du point.
    """
    def __init__(self, path, x, y, z, yaw=0, pitch=0, roll=0, parent=None, size=10):
        super().__init__(-size / 2, -size / 2, size, size)
        self.setBrush(Qt.GlobalColor.blue)
        self.setPos(x, y)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.path = path
        self.z = z
        self.yaw = yaw
        self.pitch = pitch
        self.roll = roll
        self.parent = parent

    def mousePressEvent(self, event):
        if self.parent and hasattr(self.parent, 'new_panorama'):
            self.parent.new_panorama.emit(self.path, self.yaw, self.pitch, self.roll)
        if self.parent and hasattr(self.parent, 'new_pointer_position'):
            self.parent.new_pointer_position.emit(self.pos())
        if self.parent and hasattr(self.parent, 'new_camera_position'):
            camera_position = np.array([self.pos().x(), -self.pos().y(), self.z])
            self.parent.new_camera_position.emit(camera_position)
        super().mousePressEvent(event)


class TreePoint(QGraphicsEllipseItem):
    """
    Point interactif pour les arbres sur la carte.

    Paramètres:
        x, y (float): Position dans la scène.
        tree_data (dict): Données de l'arbre.
        parent: CustomMapWidget.
        size (int): Taille du point.
    """
    def __init__(self, x, y, tree_data, parent=None, size=10):
        super().__init__(-size / 2, -size / 2, size, size)
        self.setBrush(Qt.GlobalColor.green)
        self.setPos(x, y)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        )
        self.tree_data = tree_data
        self.parent = parent
        label = QGraphicsTextItem(str(tree_data.get('No_tige', '')), self)
        label.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIgnoresTransformations)
        label.adjustSize()
        label.setPos(0, -20)

    def mousePressEvent(self, event):
        if self.parent and hasattr(self.parent, 'new_tree_attributes'):
            self.parent.new_tree_attributes.emit(self.tree_data)
        super().mousePressEvent(event)

    def paint(self, painter, option, widget=None):
        if self.isSelected():
            self.setBrush(Qt.GlobalColor.yellow)
        else:
            self.setBrush(Qt.GlobalColor.green)
        option.state &= ~QStyle.StateFlag.State_Selected
        return super().paint(painter, option, widget)
