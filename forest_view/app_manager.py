from pathlib import Path

import numpy as np
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QVBoxLayout, QWidget

from forest_view.forms import DataForm
from forest_view.io import CSV_to_dict
from forest_view.logger import get_logger
from forest_view.widgets import show_overlay
from forest_view.widgets.map import BASEMAP_OSM
from forest_view.windows import PhotoWindow, LidarWindow
from forest_view.windows.unified_window import UnifiedWindow

logger = get_logger(__name__)


class AppManager(QObject):
    def __init__(self):
        super().__init__()
        self.form = DataForm([
            ['Répertoire du projet', 'project_dir', 'répertoire'],
        ])
        self.form.exec()
        self.project_dir = Path(self.form.paths['project_dir'])
        self._open_navigation()

    def _open_navigation(self):
        """Charge les données du projet et ouvre la fenêtre unifiée (Lidar + Photo)."""
        try:
            self._open_navigation_impl()
        except Exception as e:
            logger.exception("Erreur au démarrage de la navigation")
            QMessageBox.critical(
                None,
                "Erreur",
                f"Impossible de démarrer la navigation : {e}",
            )

    def _open_navigation_impl(self):
        """Implémentation du chargement et de l'affichage."""
        try:
            self.photo_info = CSV_to_dict(
                self.project_dir / 'photo_info.csv', ','
            )
        except FileNotFoundError:
            QMessageBox.warning(
                None, 'Avertissement',
                'Le fichier photo_info.csv est introuvable dans le répertoire du projet. '
                'Les données de photos ne seront pas affichées.'
            )
            self.photo_info = None

        try:
            self.tree_info = CSV_to_dict(
                self.project_dir / 'tree_info.csv', ','
            )
        except FileNotFoundError:
            QMessageBox.warning(
                None, 'Avertissement',
                'Le fichier tree_info.csv est introuvable dans le répertoire du projet. '
                'Les données d\'arbre ne seront pas affichées.'
            )
            self.tree_info = None

        self._map_crs_epsg = getattr(self, '_map_crs_epsg', 2949)
        self._map_basemap = getattr(self, '_map_basemap', BASEMAP_OSM)
        self.photo_window = PhotoWindow(
            self.photo_info, self.tree_info,
            self.project_dir / 'panoramas',
            initial_crs_epsg=self._map_crs_epsg,
            initial_basemap_id=self._map_basemap,
        )
        self.lidar_window = LidarWindow()

        self.photo_window.tree_focus_box.checkStateChanged.connect(
            self.photo_window.gl_widget.set_tree_focus
        )
        self.photo_window.gl_widget.new_camera_direction.connect(
            self.lidar_window.update_camera_direction
        )
        self.photo_window.gl_widget.new_pointer_direction.connect(
            self.photo_window.map_widget.pointer.rotate_pointer
        )
        self.photo_window.map_widget.new_camera_position.connect(
            self.lidar_window.update_camera_position
        )
        self.photo_window.map_widget.new_camera_position.connect(
            self.photo_window.gl_widget.on_photo_selection
        )
        self.photo_window.map_widget.new_panorama.connect(
            self.photo_window.gl_widget.load_image
        )
        self.photo_window.map_widget.new_tree_attributes.connect(
            self.photo_window.propriety_widget.select_row_for_tree
        )
        self.photo_window.propriety_widget.tree_row_selected.connect(
            self.photo_window.map_widget.highlight_tree_by_data
        )
        self.lidar_window.lidar_tree_selected.connect(
            self.photo_window.map_widget.find_point
        )
        self.lidar_window.lidar_tree_selected.connect(
            self.photo_window.gl_widget.on_tree_selection
        )
        self.photo_window.map_widget.map_tree_selected.connect(
            self.lidar_window.on_map_selected_tree
        )
        self.photo_window.map_widget.map_tree_selected.connect(
            self.photo_window.gl_widget.on_tree_selection
        )

        self._unified_window = None
        self._show_unified_window()
        QApplication.processEvents()

        overlay = show_overlay(
            self._unified_window,
            "Chargement des nuages de points…",
        )
        overlay.raise_()
        QApplication.processEvents()

        project_dir = Path(self.form.paths['project_dir'])
        tree_info = self.tree_info
        photo_info = self.photo_info

        def _run_loading():
            try:
                for item in project_dir.iterdir():
                    if item.is_file() and item.suffix in ['.laz', '.las']:
                        self.lidar_window.load_point_cloud(
                            item, item.name
                        )
                        QApplication.processEvents()
                    elif item.is_file() and item.suffix == '.obj':
                        self.lidar_window.add_qsm(
                            item, item.name
                        )
                    elif item.is_dir() and item.name == 'qsm':
                        for i, obj in enumerate(item.iterdir()):
                            if obj.is_file() and obj.suffix == '.obj':
                                self.lidar_window.add_qsm(
                                    obj, obj.name
                                )
                            if i % 50 == 0:
                                QApplication.processEvents()
                    elif item.is_dir() and item.name == 'tree_clouds':
                        for i, cloud in enumerate(item.iterdir()):
                            if cloud.is_file() and cloud.suffix in ['.laz', '.las']:
                                self.lidar_window.load_point_cloud(
                                    cloud, cloud.name
                                )
                            if i % 50 == 0:
                                QApplication.processEvents()
                    else:
                        continue
                QApplication.processEvents()
                if tree_info and len(tree_info) > 0:
                    self.lidar_window.add_trees(tree_info)
                if photo_info and len(photo_info) > 0:
                    p = photo_info[0]
                    x, y, z = float(p['x']), float(p['y']), float(p['z'])
                    yaw = float(p.get('yaw', 0))
                    pitch = float(p.get('pitch', 0))
                    roll = float(p.get('roll', 0))
                    self.photo_window.gl_widget.load_image(
                        p['image'], image_yaw=yaw, image_pitch=pitch, image_roll=roll
                    )
                    self.photo_window.map_widget.set_pointer_from_data(x, y)
                    self.photo_window.map_widget.pointer.rotate_pointer(yaw)
                    self.lidar_window.update_camera_position(np.array([x, y, z]))
                    self.photo_window.gl_widget.on_photo_selection(np.array([x, y, z]))
                    QApplication.processEvents()
            finally:
                overlay.dismiss()

        QTimer.singleShot(400, _run_loading)

    def _extract_photo_content(self, photo_content):
        """Extrait gl_widget, side_panel (carte), right_container, bottom_container (propriétés + toggle)."""
        main = photo_content.layout()
        content_row = main.itemAt(0).widget()
        bottom_container = main.itemAt(1).widget()
        row_layout = content_row.layout()
        gl_widget = row_layout.itemAt(0).widget()
        right_container = row_layout.itemAt(1).widget()
        main.removeWidget(bottom_container)
        row_layout.removeWidget(right_container)
        row_layout.removeWidget(gl_widget)
        right_layout = right_container.layout()
        side_panel = right_layout.itemAt(0).widget()
        right_layout.removeWidget(side_panel)
        panorama_only = QWidget()
        lo = QVBoxLayout(panorama_only)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.addWidget(gl_widget)
        return panorama_only, side_panel, right_container, bottom_container

    def _release_vtk_before_quit(self):
        """Ferme le render window VTK/PyVista avant quit pour éviter wglMakeCurrent sur Windows."""
        try:
            if hasattr(self, 'lidar_window') and self.lidar_window is not None:
                if hasattr(self.lidar_window, 'plotter') and self.lidar_window.plotter is not None:
                    self.lidar_window.plotter.close()
        except Exception:
            pass

    def _show_unified_window(self):
        """Affiche la fenêtre unifiée (Lidar + Photo + carte + propriétés)."""
        if self._unified_window is None:
            self._unified_window = UnifiedWindow()
            self._unified_window.on_change_site_requested = self.change_site
            self._unified_window.on_crs_changed = self.set_map_crs
            self._unified_window.on_basemap_changed = self.set_map_basemap
            self._unified_window.on_lidar_vis_change = self.set_lidar_visibility
            self._unified_window._cleanup_before_quit = self._release_vtk_before_quit
        lidar_w = self.lidar_window.centralWidget()
        photo_content = self.photo_window.centralWidget()
        panorama_w, side_panel, right_container, bottom_container = self._extract_photo_content(photo_content)
        self._unified_window.set_widgets(lidar_w, panorama_w, side_panel, right_container, bottom_container)
        self.lidar_window.setCentralWidget(QWidget())
        self.photo_window.setCentralWidget(QWidget())
        self.lidar_window.hide()
        self.photo_window.hide()
        self._unified_window.set_basemap_checked(self._map_basemap)
        self._unified_window.show()
        self._unified_window.raise_()
        self._unified_window.activateWindow()

    def set_map_crs(self, epsg: int):
        """Change le CRS de la carte et redessine avec les mêmes données."""
        self._map_crs_epsg = int(epsg)
        self.photo_window.gl_widget.new_pointer_direction.disconnect()
        self.photo_window.replot_map(
            self.photo_info, self.tree_info, self._map_crs_epsg
        )

    def set_map_basemap(self, provider_id: str):
        """Change le fond de carte et rafraîchit les tuiles."""
        self._map_basemap = provider_id
        self.photo_window.map_widget.set_basemap(provider_id)
        self.photo_window.map_widget.add_osm_base_map()
        if self._unified_window is not None:
            self._unified_window.set_basemap_checked(provider_id)

    def set_lidar_visibility(self, group, state):
        self.lidar_window.set_visibility(group, state)

    def change_site(self):
        """Demande confirmation, ferme les fenêtres de navigation et retourne au choix du projet."""
        parent = (self._unified_window if (self._unified_window and self._unified_window.isVisible())
                  else self.photo_window)
        mb = QMessageBox(parent)
        mb.setWindowTitle("Changer de site")
        mb.setText("Voulez-vous vraiment quitter la navigation ?")
        oui = mb.addButton("Oui", QMessageBox.ButtonRole.YesRole)
        non = mb.addButton("Non", QMessageBox.ButtonRole.NoRole)
        mb.setDefaultButton(non)
        mb.exec()
        if mb.clickedButton() != oui:
            return

        self.photo_window._returning_to_project_selection = True
        self.lidar_window._returning_to_project_selection = True
        if self._unified_window is not None and self._unified_window.isVisible():
            self._unified_window._returning_to_project_selection = True
            self._unified_window.close()
        self.lidar_window.close()
        self.photo_window.close()
        self.form._change_site_context = True
        self.form.show()
        self.form.raise_()
        self.form.activateWindow()
        result = self.form.exec()
        if result != QDialog.DialogCode.Accepted:
            return
        self._open_navigation()
