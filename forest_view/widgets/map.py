from PyQt6.QtCore import Qt, QPointF, QObject, pyqtSignal, QMarginsF
from PyQt6.QtGui import QColor, QPainter, QPolygonF
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsView,
    QGraphicsItem,
    QGraphicsPolygonItem,
)

from forest_view.widgets.map_items import PhotoPoint, TreePoint


class Pointer(QGraphicsPolygonItem, QObject):
    """Pointeur indiquant la position et la direction de la caméra sur la carte."""
    def __init__(self):
        super().__init__(QPolygonF([
            QPointF(0, -10), QPointF(7, 10), QPointF(0, 4), QPointF(-7, 10), QPointF(0, -10)
        ]))
        self.setBrush(Qt.GlobalColor.red)
        self.setPos(0, 0)
        self.setTransformOriginPoint(0, 0)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setZValue(1)

    def rotate_pointer(self, angle):
        self.setRotation(angle)
        self.setTransformOriginPoint(0, 0)


class CustomMapWidget(QGraphicsView):
    """Carte des points d'intérêt (photos et arbres)."""
    new_camera_position = pyqtSignal(object)
    new_pointer_position = pyqtSignal(object)
    new_panorama = pyqtSignal(str, float, float, float)
    new_tree_attributes = pyqtSignal(object)
    map_tree_selected = pyqtSignal(object)

    def __init__(self, photo_coordinates, tree_coordinates=None):
        super().__init__()
        self.last_selection = []
        self.scene = QGraphicsScene()
        self.scene.selectionChanged.connect(self.on_selection_change)
        self.setScene(self.scene)
        self.setMinimumSize(100, 100)
        self.setBackgroundBrush(QColor(200, 200, 200))

        if photo_coordinates is not None:
            self.plot_photo_coordinates(photo_coordinates)
        if tree_coordinates is not None:
            self.plot_tree_coordinates(tree_coordinates)

        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.scene.setSceneRect(self.scene.itemsBoundingRect().marginsAdded(QMarginsF(10, 10, 10, 10)))
        self.create_pointer()

    def plot_photo_coordinates(self, photo_coordinates):
        """Affiche les points de photos sur la carte."""
        if not photo_coordinates:
            return
        for entry in photo_coordinates:
            path = entry['image']
            scene_x = float(entry['x'])
            scene_y = -float(entry['y'])
            scene_z = float(entry['z'])
            yaw = float(entry.get('yaw', 0))
            pitch = float(entry.get('pitch', 0))
            roll = float(entry.get('roll', 0))
            point = PhotoPoint(path, scene_x, scene_y, scene_z, yaw, pitch, roll, self, 10)
            self.scene.addItem(point)

    def plot_tree_coordinates(self, tree_coordinates):
        """Affiche les points d'arbres sur la carte."""
        if not tree_coordinates:
            return
        for entry in tree_coordinates:
            scene_x = float(entry.get('x'))
            scene_y = -float(entry.get('y'))
            scene_z = float(entry.get('z'))

            tree_data = {k: v for k, v in entry.items() if k not in {'x', 'y', 'z'}}
            point = TreePoint(scene_x, scene_y, scene_z, tree_data, self, 10)
            self.scene.addItem(point)

    def create_pointer(self):
        if not hasattr(self, 'pointer') or self.pointer is None:
            self.pointer = Pointer()
            self.scene.addItem(self.pointer)
            self.new_pointer_position.connect(self.pointer.setPos)

    def reset(self):
        self.last_selection = []
        try:
            self.new_pointer_position.disconnect()
        except TypeError:
            pass
        self.scene.clear()
        self.pointer = None
        self.create_pointer()
        self.new_pointer_position.connect(self.pointer.setPos)
        self.last_selection = []
        self.scene.clearSelection()

    def wheelEvent(self, event):
        factor = 1.2
        if event.angleDelta().y() < 0:
            factor = 1.0 / factor
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        self.last_selection = self.scene.selectedItems()
        return super().mousePressEvent(event)

    def on_selection_change(self):
        if not self.scene.selectedItems() and self.last_selection:
            for item in self.last_selection:
                item.setSelected(True)

    def find_point(self, position):
        x = position[0]
        y = -position[1]
        items = self.scene.items(QPointF(x, y))
        for item in items:
            if isinstance(item, TreePoint):
                if item.pos() == QPointF(x, y):
                    self.last_selection = []
                    self.scene.clearSelection()
                    item.setSelected(True)
                    self.new_tree_attributes.emit(item.tree_data)
                    break
