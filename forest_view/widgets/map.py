import math
import urllib.request

import numpy as np
from PyQt6.QtCore import Qt, QPointF, QObject, pyqtSignal, QMarginsF, QRectF
from PyQt6.QtGui import QColor, QPainter, QPixmap, QPolygonF, QTransform
from PyQt6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QGraphicsItem,
    QGraphicsPolygonItem,
    QLabel,
)

from forest_view.crs_utils import data_to_wgs84
from forest_view.widgets.map_items import PhotoPoint, TreePoint

TILE_SIZE = 256
OSM_USER_AGENT = "UdeSForestView/1.0"

BASEMAP_OSM = "osm"
BASEMAP_PROVIDERS = {
    BASEMAP_OSM: {
        "label": "OpenStreetMap",
        "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attribution": "© OpenStreetMap contributors",
        "attribution_url": "https://www.openstreetmap.org/copyright",
    },
}


def _lon_to_tile_x(lon_deg, z):
    n = 2 ** z
    return (lon_deg + 180) / 360 * n


def _lat_to_tile_y(lat_deg, z):
    lat_rad = math.radians(lat_deg)
    n = 2 ** z
    return (1 - math.asinh(math.tan(lat_rad)) / math.pi) / 2 * n


def _tile_x_to_lon(tx, z):
    n = 2 ** z
    return tx / n * 360 - 180


def _tile_y_to_lat(ty, z):
    n = 2 ** z
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ty / n)))
    return math.degrees(lat_rad)


def _fetch_tile(z, x, y, url_template):
    """Télécharge une tuile et retourne un QPixmap, ou None en cas d'échec."""
    url = url_template.format(z=z, x=x, y=y)
    req = urllib.request.Request(url, headers={"User-Agent": OSM_USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        pix = QPixmap()
        if pix.loadFromData(data):
            return pix
    except Exception:
        pass
    return None


def _tree_data_match(a, b):
    """Compare deux dicts tree_data. Utilise No_tige si présent, sinon égalité."""
    if not a or not b:
        return a == b
    if 'No_tige' in a and 'No_tige' in b:
        return a.get('No_tige') == b.get('No_tige')
    return a == b


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
        self.setZValue(20)

    def rotate_pointer(self, angle):
        self.setRotation(angle)
        self.setTransformOriginPoint(0, 0)


class CustomMapWidget(QGraphicsView):
    """Carte des points d'intérêt (photos et arbres). Scène en WGS84 (lon, -lat) ; données reprojetées depuis crs_epsg."""
    new_camera_position = pyqtSignal(object)
    new_pointer_position = pyqtSignal(object)
    new_panorama = pyqtSignal(str, float, float, float)
    new_tree_attributes = pyqtSignal(object)
    map_tree_selected = pyqtSignal(object)

    def __init__(self, photo_coordinates, tree_coordinates=None, crs_epsg=4326, basemap_id=None):
        super().__init__()
        self._crs_epsg = int(crs_epsg)
        self._basemap_id = basemap_id if basemap_id in BASEMAP_PROVIDERS else BASEMAP_OSM
        self.last_selection = []
        self.scene = QGraphicsScene(self)
        self.scene.selectionChanged.connect(self.on_selection_change)
        self.setScene(self.scene)
        self.setMinimumSize(100, 100)
        self.setBackgroundBrush(QColor(200, 200, 200))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        if photo_coordinates is not None:
            self.plot_photo_coordinates(photo_coordinates)
        if tree_coordinates is not None:
            self.plot_tree_coordinates(tree_coordinates)

        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._osm_tile_items = []
        self.add_osm_base_map()
        self.fit_extent_to_dataset()
        self.create_pointer()
        self._create_osm_attribution()

    def set_crs(self, epsg: int):
        """Change le CRS des données (ex. 2949). L'appelant doit redessiner les points."""
        self._crs_epsg = int(epsg)

    def set_basemap(self, provider_id: str):
        """Change le fond de carte (ex. osm). L'appelant peut rappeler add_osm_base_map pour rafraîchir les tuiles."""
        if provider_id in BASEMAP_PROVIDERS:
            self._basemap_id = provider_id

    def get_basemap_id(self):
        """Retourne l'identifiant du fond de carte actuel."""
        return self._basemap_id

    def set_pointer_from_data(self, x_data: float, y_data: float):
        """Positionne le pointeur à partir de coordonnées dans le CRS des données (ex. MTM)."""
        lon, lat = data_to_wgs84(x_data, y_data, self._crs_epsg)
        if self.pointer:
            self.pointer.setPos(lon, -lat)

    def plot_photo_coordinates(self, photo_coordinates):
        """Affiche les points de photos. Reprojection à la volée : crs_epsg → WGS84 (4326) pour la scène et OSM."""
        if not photo_coordinates:
            return
        for i, entry in enumerate(photo_coordinates):
            path = entry['image']
            x_data = float(entry['x'])
            y_data = float(entry['y'])
            scene_z = float(entry['z'])
            lon, lat = data_to_wgs84(x_data, y_data, self._crs_epsg)
            scene_x, scene_y = lon, -lat
            yaw = float(entry.get('yaw', 0))
            pitch = float(entry.get('pitch', 0))
            roll = float(entry.get('roll', 0))
            is_origin = i == 0
            size = 14 if is_origin else 10
            point = PhotoPoint(
                path, scene_x, scene_y, scene_z, yaw, pitch, roll, self, size, is_origin=is_origin,
                data_x=x_data, data_y=y_data
            )
            self.scene.addItem(point)

    def plot_tree_coordinates(self, tree_coordinates):
        """Affiche les points d'arbres. Reprojection à la volée : crs_epsg → WGS84 (4326) pour la scène et OSM."""
        if not tree_coordinates:
            return
        for row_index, entry in enumerate(tree_coordinates):
            x_data = float(entry.get('x'))
            y_data = float(entry.get('y'))
            scene_z = float(entry.get('z'))
            lon, lat = data_to_wgs84(x_data, y_data, self._crs_epsg)
            scene_x, scene_y = lon, -lat
            tree_data = {k: v for k, v in entry.items() if k not in {'x', 'y', 'z'}}
            point = TreePoint(
                scene_x, scene_y, scene_z, tree_data, self, 10,
                data_x=x_data, data_y=y_data, row_index=row_index
            )
            self.scene.addItem(point)

    def _data_bounds(self):
        """Retourne (lon_min, lon_max, lat_min, lat_max) en WGS84 (degrés) à partir des points (scène : x=lon, y=-lat)."""
        lon_min = lat_min = float('inf')
        lon_max = lat_max = float('-inf')
        for item in self.scene.items():
            if isinstance(item, (PhotoPoint, TreePoint)):
                p = item.pos()
                lon_min = min(lon_min, p.x())
                lon_max = max(lon_max, p.x())
                lat = -p.y()
                lat_min = min(lat_min, lat)
                lat_max = max(lat_max, lat)
        if lon_min == float('inf'):
            return None
        return (lon_min, lon_max, lat_min, lat_max)

    def _scene_rect_from_data(self, margin_ratio=0.15):
        """QRectF couvrant l’étendue des données (WGS84) avec marge, None si aucun point."""
        bounds = self._data_bounds()
        if not bounds:
            return None
        lon_min, lon_max, lat_min, lat_max = bounds
        span_lon = max(lon_max - lon_min, 0.0001)
        span_lat = max(lat_max - lat_min, 0.0001)
        margin_lon = span_lon * margin_ratio
        margin_lat = span_lat * margin_ratio
        lon_min -= margin_lon
        lon_max += margin_lon
        lat_min -= margin_lat
        lat_max += margin_lat
        return QRectF(
            lon_min, -lat_max,
            lon_max - lon_min, lat_max - lat_min
        )

    def fit_extent_to_dataset(self):
        """Ajuste la vue et la scene rect sur l’étendue des données (avec marge). Rien si aucun point."""
        rect = self._scene_rect_from_data()
        if rect is None:
            rect = self.scene.itemsBoundingRect()
            if rect.isNull() or rect.isEmpty():
                return
        self.scene.setSceneRect(rect.marginsAdded(QMarginsF(10, 10, 10, 10)))
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def add_osm_base_map(self):
        """Ajoute une couche de tuiles OSM en fond. La scène est en WGS84 (lon, -lat en degrés) ;
        les données sont reprojetées à la volée depuis crs_epsg vers 4326."""
        bounds = self._data_bounds()
        if not bounds:
            return
        lon_min, lon_max, lat_min, lat_max = bounds
        lon_min = max(-180.0, min(180.0, lon_min))
        lon_max = max(-180.0, min(180.0, lon_max))
        lat_min = max(-90.0, min(90.0, lat_min))
        lat_max = max(-90.0, min(90.0, lat_max))
        if lon_min >= lon_max:
            lon_max = lon_min + 0.001
        if lat_min >= lat_max:
            lat_max = lat_min + 0.001
        margin = max(0.0001, (lon_max - lon_min) * 0.1, (lat_max - lat_min) * 0.1)
        lon_min -= margin
        lon_max += margin
        lat_min -= margin
        lat_max += margin
        n_tiles_lon = max(1, (lon_max - lon_min) / 360 * (2 ** 18))
        z = min(19, max(0, int(18 - math.log2(n_tiles_lon))))
        n = 2 ** z
        tx_min = int(math.floor(_lon_to_tile_x(lon_min, z)))
        tx_max = int(math.ceil(_lon_to_tile_x(lon_max, z)))
        ty_min = int(math.floor(_lat_to_tile_y(lat_max, z)))
        ty_max = int(math.ceil(_lat_to_tile_y(lat_min, z)))
        tx_max = max(tx_min + 1, tx_max)
        ty_max = max(ty_min + 1, ty_max)
        for item in self._osm_tile_items:
            self.scene.removeItem(item)
        self._osm_tile_items.clear()
        provider = BASEMAP_PROVIDERS.get(self._basemap_id, BASEMAP_PROVIDERS[BASEMAP_OSM])
        url_template = provider["url"]
        for ty in range(ty_min, ty_max):
            for tx in range(tx_min, tx_max):
                pix = _fetch_tile(z, tx, ty, url_template)
                if pix is None:
                    continue
                scene_left = _tile_x_to_lon(tx, z)
                scene_right = _tile_x_to_lon(tx + 1, z)
                scene_top = -_tile_y_to_lat(ty, z)
                scene_bottom = -_tile_y_to_lat(ty + 1, z)
                tile_item = QGraphicsPixmapItem(pix)
                tile_item.setZValue(-1000)
                tile_item.setPos(scene_left, scene_top)
                scale_x = (scene_right - scene_left) / TILE_SIZE
                scale_y = (scene_bottom - scene_top) / TILE_SIZE
                tile_item.setTransform(QTransform.fromScale(scale_x, scale_y))
                self.scene.addItem(tile_item)
                self._osm_tile_items.append(tile_item)
        self._stack_points_above_basemap()
        self._update_attribution()

    def _stack_points_above_basemap(self):
        """Place les points (photos, arbres) au-dessus des tuiles OSM pour qu’ils restent visibles."""
        for item in self.scene.items():
            if isinstance(item, (PhotoPoint, TreePoint)):
                item.setZValue(10)

    def create_pointer(self):
        if not hasattr(self, 'pointer') or self.pointer is None:
            self.pointer = Pointer()
            self.scene.addItem(self.pointer)
            self.new_pointer_position.connect(self.pointer.setPos)

    def _create_osm_attribution(self):
        """Crée le label d'attribution du fond de carte en bas à gauche."""
        self._osm_attribution_label = QLabel(self)
        self._osm_attribution_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._osm_attribution_label.setStyleSheet(
            "background-color: rgba(255, 255, 255, 180); color: #333; padding: 2px 6px; font-size: 10px; border-radius: 2px;"
        )
        self._osm_attribution_label.setOpenExternalLinks(True)
        self._update_attribution()
        self._update_osm_attribution_geometry()

    def _update_attribution(self):
        """Met à jour le texte d'attribution selon le fond de carte actuel."""
        if getattr(self, '_osm_attribution_label', None) is None:
            return
        provider = BASEMAP_PROVIDERS.get(self._basemap_id, BASEMAP_PROVIDERS[BASEMAP_OSM])
        text = provider["attribution"]
        url = provider.get("attribution_url", "")
        if url:
            self._osm_attribution_label.setText(
                '<a href="%s" style="color:#1967b2;">%s</a>' % (url, text)
            )
        else:
            self._osm_attribution_label.setText(text)
        self._osm_attribution_label.adjustSize()
        self._update_osm_attribution_geometry()

    def _update_osm_attribution_geometry(self):
        if getattr(self, '_osm_attribution_label', None) is None:
            return
        margin = 6
        w = self._osm_attribution_label.sizeHint().width()
        h = self._osm_attribution_label.sizeHint().height()
        self._osm_attribution_label.setGeometry(margin, self.height() - h - margin, w, h)
        self._osm_attribution_label.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_osm_attribution_geometry()

    def reset(self):
        self.last_selection = []
        self._osm_tile_items = []
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
        """Reçoit une position en CRS des données (ex. MTM). Transforme en scène (WGS84) pour retrouver le point."""
        x_data, y_data = position[0], position[1]
        lon, lat = data_to_wgs84(x_data, y_data, self._crs_epsg)
        scene_x, scene_y = lon, -lat
        items = self.scene.items(QPointF(scene_x, scene_y))
        for item in items:
            if isinstance(item, TreePoint):
                if item.pos() == QPointF(scene_x, scene_y):
                    self.last_selection = []
                    self.scene.clearSelection()
                    item.setSelected(True)
                    self.new_tree_attributes.emit(item.tree_data)
                    break

    def highlight_tree_by_data(self, payload):
        """Sélectionne sur la carte le point d'arbre correspondant à la ligne table (sans déplacer la vue).
        payload = (row_index, tree_data) depuis la table, ou tree_data seul depuis la carte."""
        row_index = None
        if isinstance(payload, (list, tuple)) and len(payload) == 2:
            row_index, tree_data = payload[0], payload[1]
        else:
            tree_data = payload
        if not tree_data:
            return
        self.last_selection = []
        self.scene.clearSelection()
        item = None
        if row_index is not None:
            for it in self.scene.items():
                if isinstance(it, TreePoint) and getattr(it, 'row_index', None) == row_index:
                    item = it
                    break
        if item is None:
            for it in self.scene.items():
                if isinstance(it, TreePoint) and _tree_data_match(it.tree_data, tree_data):
                    item = it
                    break
        if item is not None:
            item.setSelected(True)
            if item.data_x is not None and item.data_y is not None:
                tree_position = np.array([item.data_x, item.data_y, item.z])
            else:
                px, py = item.pos().x(), item.pos().y()
                tree_position = np.array([px, -py, item.z])
            self.map_tree_selected.emit(tree_position)
