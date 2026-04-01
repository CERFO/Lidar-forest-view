from pathlib import Path

import numpy as np
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QVBoxLayout, QWidget

from forest_view.forms import DataForm
from forest_view.io import CSV_to_dict, writeCSV
from forest_view.logger import get_logger
from forest_view.widgets import show_overlay
from forest_view.widgets.map import BASEMAP_OSM
from forest_view.windows import PhotoWindow, LidarWindow
from forest_view.windows.unified_window import UnifiedWindow

logger = get_logger(__name__)


class AppManager(QObject):
    def __init__(self):
        super().__init__()
        self._map_crs_epsg = 2949
        self._map_basemap = BASEMAP_OSM
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
        self.photo_window.map_widget.map_tree_deleted.connect(
            self.lidar_window.remove_tree_at
        )
        self.photo_window.propriety_widget.saved_data.connect(
            self.update_tree_info
        )
        self.photo_window.propriety_widget.tree_row_selected.connect(
            self.photo_window.map_widget.highlight_tree_by_data
        )
        self.photo_window.propriety_widget.tree_data_changed.connect(
            self.photo_window.map_widget.update_tree_data
        )
        self.photo_window.propriety_widget.row_removed.connect(
            self.photo_window.map_widget.remove_tree
        )
        self.photo_window.propriety_widget.new_tree_pos_requested.connect(
            self.lidar_window.on_pos_request
        )
        self.photo_window.propriety_widget.new_tree.connect(
            self.photo_window.map_widget.plot_tree_coordinates
        )
        self.photo_window.propriety_widget.new_tree_position.connect(
            self.lidar_window.add_tree
        )
        self.lidar_window.lidar_tree_selected.connect(
            self.photo_window.map_widget.highlight_tree_by_location
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

        tree_info = self.tree_info
        photo_info = self.photo_info

        def _run_loading():
            try:
                for i, item in enumerate(self.project_dir.rglob('*')):
                    if item.suffix in ['.laz', '.las']:
                        self.lidar_window.load_point_cloud(
                            item, item.name
                        )
                    elif item.suffix == '.obj':
                        self.lidar_window.add_qsm(
                            item, item.name
                        )
                    else:
                        continue

                    if i % 30 == 0:
                                QApplication.processEvents()

                QApplication.processEvents()
                if tree_info and len(tree_info) > 0:
                    self.lidar_window.add_all_trees(tree_info)
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
                    self.lidar_window.set_forward_view_from_yaw(yaw)
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
            self._bind_unified_lidar_controls()
            self._unified_window._cleanup_before_quit = self._release_vtk_before_quit
        lidar_w = self.lidar_window.centralWidget()
        photo_content = self.photo_window.centralWidget()
        panorama_w, side_panel, right_container, bottom_container = self._extract_photo_content(photo_content)
        self._unified_window.set_widgets(lidar_w, panorama_w, side_panel, right_container, bottom_container)
        self.lidar_window.setCentralWidget(QWidget())
        self.photo_window.setCentralWidget(QWidget())
        self.lidar_window.hide()
        self.photo_window.hide()
        trees_count = len(self.tree_info) if self.tree_info else 0
        photos_count = len(self.photo_info) if self.photo_info else 0
        self._unified_window.set_vector_counts(trees_count, photos_count)
        self._unified_window.set_current_point_color(self.lidar_window.get_current_point_color())
        self._unified_window.set_basemap_checked(self._map_basemap)
        self._unified_window.show()
        self._unified_window.raise_()
        self._unified_window.activateWindow()

    def _bind_unified_lidar_controls(self):
        """
        Relie les contrôles du menu Lidar à la vue 3D.

        Comportement attendu des options :
        - Taille des points : taille de base utilisée par les nuages.
        - Taille adaptative : ajuste cette taille de base selon la distance caméra/focale.
        - Profondeur adaptative : distance des premiers mètres où la taille passe de 10 à la taille de base.
        - Réinitialiser la vue : revient au point de vue aligné sur la photo courante.
        - Lock world up : contraint le haut de la caméra sur +Z (horizon stable).
        - Couleur des points : applique la couleur aux nuages existants et futurs.
        """
        self._unified_window.on_lidar_vis_change = self.set_lidar_visibility
        self._unified_window.on_lidar_point_size_change = self.set_lidar_point_size
        self._unified_window.on_lidar_adaptive_point_size_change = self.set_lidar_adaptive_point_size
        self._unified_window.on_lidar_adaptive_max_depth_change = self.set_lidar_adaptive_max_depth
        self._unified_window.on_lidar_reset_view_requested = self.reset_lidar_view
        self._unified_window.on_lidar_lock_world_up_change = self.set_lidar_lock_world_up
        self._unified_window.on_lidar_point_color_change = self.set_lidar_point_color
        self._unified_window.on_vector_visibility_change = self.set_vector_visibility

    def set_map_crs(self, epsg: int):
        """Change le CRS de la carte et redessine avec les mêmes données."""
        self._map_crs_epsg = int(epsg)
        try:
            self.photo_window.gl_widget.new_pointer_direction.disconnect()
        except TypeError:
            pass
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

    def set_lidar_point_size(self, size):
        self.lidar_window.set_point_size(size)

    def set_lidar_adaptive_point_size(self, state):
        self.lidar_window.set_adaptive_point_size(state)

    def set_lidar_adaptive_max_depth(self, max_depth):
        self.lidar_window.set_adaptive_max_depth(max_depth)

    def reset_lidar_view(self):
        self.lidar_window.reset_view()

    def set_lidar_lock_world_up(self, state):
        self.lidar_window.set_lock_world_up(state)

    def set_lidar_point_color(self, color_rgb):
        self.lidar_window.set_point_color(color_rgb)
        if self._unified_window is not None:
            self._unified_window.set_current_point_color(color_rgb)

    def set_vector_visibility(self, layer, state):
        if layer == 'trees':
            self.lidar_window.set_visibility('trees', state)
        self.photo_window.map_widget.set_layer_visibility(layer, state)

    def update_tree_info(self, list_of_dicts, deleted_rows, new_rows:int):
        for row in deleted_rows:
            del self.tree_info[row]
        for i in range(new_rows):
            keys = self.tree_info[0].keys()
            self.tree_info.append(dict.fromkeys(keys))
        for i, tree_data in enumerate(list_of_dicts):
            self.tree_info[i].update(tree_data)
        writeCSV(self.project_dir / 'tree_info.csv', self.tree_info)
        if self._unified_window is not None:
            photos_count = len(self.photo_info) if self.photo_info else 0
            self._unified_window.set_vector_counts(len(self.tree_info), photos_count)

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
        self.project_dir = Path(self.form.paths['project_dir'])
        if result != QDialog.DialogCode.Accepted:
            return
        self._open_navigation()
