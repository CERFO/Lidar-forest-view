from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QInputDialog,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QSplitter,
    QSplitterHandle,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
    QCheckBox
)


class PanoramaMapOverlayContainer(QWidget):
    """Conteneur : panorama en fond, panneau carte en overlay (plein écran sur le panorama)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._panorama = None
        self._map_panel = None

    def set_panels(self, panorama_widget, map_panel):
        if self._panorama:
            self._panorama.setParent(None)
        if self._map_panel:
            self._map_panel.setParent(None)
        self._panorama = panorama_widget
        self._map_panel = map_panel
        if panorama_widget:
            panorama_widget.setParent(self)
        if map_panel:
            map_panel.setParent(self)
            map_panel.setMinimumSize(0, 0)
            map_panel.setMaximumSize(16777215, 16777215)
            map_panel.raise_()
        self._update_geometries()

    def _update_geometries(self):
        r = self.rect()
        if self._panorama:
            self._panorama.setGeometry(r)
        if self._map_panel:
            width = int(r.width()/3)
            height = int(r.height()/3)
            left = r.width() - width
            self._map_panel.setGeometry(QRect(left, 0, width, height))
            self._map_panel.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_geometries()


class UnifiedSplitterHandle(QSplitterHandle):
    """Poignée du splitter plus visible pour redimensionner les deux panneaux."""
    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)
        self.setCursor(
            Qt.CursorShape.SizeHorCursor if orientation == Qt.Orientation.Horizontal
            else Qt.CursorShape.SizeVerCursor
        )


class ResizableSplitter(QSplitter):
    """Splitter qui utilise une poignée plus visible."""
    def createHandle(self):
        return UnifiedSplitterHandle(self.orientation(), self)


class UnifiedWindow(QMainWindow):
    """
    Fenêtre unifiée : Lidar et Photo côte à côte, avec carte et propriétés
    en bandeau droit et bas sur toute la fenêtre (modals sur fenêtre entière).
    """
    HANDLE_WIDTH = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("UdeS Forest View")
        self.setGeometry(100, 100, 1200, 600)
        self.on_change_site_requested = None
        self.on_crs_changed = None
        self.on_basemap_changed = None
        self.on_lidar_vis_change = None
        self._lidar_widget = None
        self._panorama_container = None
        self._right_container = None
        self._bottom_container = None

        menu_bar = QMenuBar(self)
        menu_fichier = QMenu("Fichier", self)
        self._action_changer_site = QAction("Changer de site", self)
        self._action_changer_site.triggered.connect(self._on_changer_site)
        menu_fichier.addAction(self._action_changer_site)
        self._action_quitter = QAction("Quitter", self)
        self._action_quitter.triggered.connect(self.close)
        menu_fichier.addAction(self._action_quitter)
        menu_bar.addMenu(menu_fichier)

        menu_carte = QMenu("Carte", self)
        menu_crs = QMenu("SRC", self)
        self._crs_actions = {}
        for epsg, label in [
            (2949, "EPSG:2949 – NAD83(CSRS) / MTM zone 7"),
            (4326, "EPSG:4326 – WGS84"),
        ]:
            action = QAction(label, self)
            action.triggered.connect(lambda checked=False, e=epsg: self._on_crs_selected(e))
            menu_crs.addAction(action)
            self._crs_actions[epsg] = action
        action_autre = QAction("Autre…", self)
        action_autre.triggered.connect(self._on_crs_autre)
        menu_crs.addAction(action_autre)
        menu_carte.addMenu(menu_crs)

        menu_fond = QMenu("Fond de carte", self)
        self._basemap_actions = {}
        from forest_view.widgets.map import BASEMAP_OSM, BASEMAP_PROVIDERS
        for provider_id, info in BASEMAP_PROVIDERS.items():
            action = QAction(info["label"], self)
            action.setCheckable(True)
            action.setChecked(provider_id == BASEMAP_OSM)
            action.triggered.connect(lambda checked=False, pid=provider_id: self._on_basemap_selected(pid))
            menu_fond.addAction(action)
            self._basemap_actions[provider_id] = action
        menu_carte.addMenu(menu_fond)
        menu_bar.addMenu(menu_carte)

        menu_lidar = QMenu('Lidar', self)
        qsm_vis_box = QCheckBox('QSM', self)
        qsm_vis_box.setChecked(True)
        qsm_vis_box.stateChanged.connect(lambda s=qsm_vis_box.isChecked(): self._on_visibility_change('qsm', s))
        qsm_vis_act = QWidgetAction(self)
        qsm_vis_act.setDefaultWidget(qsm_vis_box)
        menu_lidar.addAction(qsm_vis_act)
        cloud_vis_box = QCheckBox('Nuages de points', self)
        cloud_vis_box.setChecked(True)
        cloud_vis_box.stateChanged.connect(lambda s=cloud_vis_box.isChecked(): self._on_visibility_change('cloud', s))
        cloud_vis_act = QWidgetAction(self)
        cloud_vis_act.setDefaultWidget(cloud_vis_box)
        menu_lidar.addAction(cloud_vis_act)
        menu_bar.addMenu(menu_lidar)
        self.setMenuBar(menu_bar)

        self.splitter = ResizableSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(self.HANDLE_WIDTH)
        self.splitter.setStyleSheet(
            f"QSplitter::handle {{"
            f" width: {self.HANDLE_WIDTH}px;"
            f" background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            f" stop:0 #c0c0c0, stop:0.5 #e0e0e0, stop:1 #c0c0c0);"
            f" margin: 0 2px;"
            f" border-left: 1px solid #a0a0a0;"
            f" border-right: 1px solid #a0a0a0;"
            f"}}"
        )

        central = QWidget()
        self._main_layout = QVBoxLayout(central)
        self._main_layout.setContentsMargins(4, 4, 4, 4)
        self._main_layout.setSpacing(4)

        self._top_row = QWidget()
        self._top_row_layout = QHBoxLayout(self._top_row)
        self._top_row_layout.setContentsMargins(0, 0, 0, 0)
        self._top_row_layout.setSpacing(4)
        self._top_row_layout.addWidget(self.splitter, 1)
        self._main_layout.addWidget(self._top_row, 1)
        self.setCentralWidget(central)

    def set_widgets(self, lidar_widget, panorama_widget, map_panel, right_container, bottom_container):
        """Affiche les vues : splitter (Lidar | Panorama+carte), bandeau droit, bandeau bas (propriétés + toggle)."""
        self.take_widgets()
        self._lidar_widget = lidar_widget
        self._right_container = right_container
        self._bottom_container = bottom_container

        panorama_container = PanoramaMapOverlayContainer()
        panorama_container.set_panels(panorama_widget, map_panel)
        self._panorama_container = panorama_container

        min_pane = 150
        if lidar_widget:
            lidar_widget.setMinimumWidth(min_pane)
            self.splitter.addWidget(lidar_widget)
        panorama_container.setMinimumWidth(min_pane)
        self.splitter.addWidget(panorama_container)
        if self.splitter.count() >= 2:
            half = max(min_pane, self.splitter.width() // 2)
            self.splitter.setSizes([half, half])

        if right_container:
            self._top_row_layout.addWidget(right_container, 0)
        if bottom_container:
            self._main_layout.insertWidget(1, bottom_container, 0)

    def take_widgets(self):
        """Retire tous les widgets et les retourne (lidar, panorama, map_panel, right_container, bottom_container)."""
        lidar_w = self._lidar_widget
        right_w = self._right_container
        bottom_w = self._bottom_container
        panorama_w = None
        map_panel = None
        if self._panorama_container:
            panorama_w = self._panorama_container._panorama
            map_panel = self._panorama_container._map_panel
            self._panorama_container.set_panels(None, None)
            self.splitter.removeWidget(self._panorama_container)
            self._panorama_container = None
        if lidar_w:
            self.splitter.removeWidget(lidar_w)
        if right_w:
            self._top_row_layout.removeWidget(right_w)
        if bottom_w:
            self._main_layout.removeWidget(bottom_w)
        self._lidar_widget = None
        self._right_container = None
        self._bottom_container = None
        return (lidar_w, panorama_w, map_panel, right_w, bottom_w)

    def _on_changer_site(self):
        if callable(self.on_change_site_requested):
            self.on_change_site_requested()

    def _on_crs_selected(self, epsg: int):
        if callable(self.on_crs_changed):
            self.on_crs_changed(epsg)

    def _on_basemap_selected(self, provider_id: str):
        for pid, action in self._basemap_actions.items():
            action.setChecked(pid == provider_id)
        if callable(self.on_basemap_changed):
            self.on_basemap_changed(provider_id)

    def _on_visibility_change(self, group, state):
        if callable(self.on_lidar_vis_change):
            self.on_lidar_vis_change(group, state)

    def set_basemap_checked(self, provider_id: str):
        """Met à jour la coche du menu Fond de carte (ex. après chargement d'un projet)."""
        for pid, action in self._basemap_actions.items():
            action.setChecked(pid == provider_id)

    def _on_crs_autre(self):
        epsg_str, ok = QInputDialog.getText(
            self,
            "CRS",
            "Code EPSG (ex. 2949, 4326):",
            text="2949",
        )
        if not ok or not epsg_str:
            return
        try:
            epsg = int(epsg_str.strip())
        except ValueError:
            QMessageBox.warning(
                self,
                "CRS",
                "Code EPSG invalide. Entrez un nombre (ex. 2949).",
            )
            return
        if callable(self.on_crs_changed):
            self.on_crs_changed(epsg)

    def closeEvent(self, event):
        if getattr(self, '_returning_to_project_selection', False):
            event.accept()
            return
        reply = QMessageBox.question(
            self,
            "Quitter",
            "Êtes-vous sûr de vouloir quitter l'application ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if callable(getattr(self, '_cleanup_before_quit', None)):
                self._cleanup_before_quit()
            event.accept()
            QApplication.quit()
        else:
            event.ignore()
