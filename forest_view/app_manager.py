import os

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

from forest_view.forms import DataForm
from forest_view.io import CSV_to_dict
from forest_view.logger import get_logger
from forest_view.widgets import show_overlay
from forest_view.windows import PhotoWindow, LidarWindow

logger = get_logger(__name__)


class AppManager(QObject):
    def __init__(self):
        super().__init__()
        self.form = DataForm([
            ['Répertoire du projet', 'project_dir', 'répertoire'],
        ])
        self.form.exec()
        self._open_navigation()

    def _open_navigation(self):
        """Charge les données du projet et ouvre les fenêtres photo + lidar."""
        try:
            self.photo_info = CSV_to_dict(
                os.path.join(self.form.paths['project_dir'], 'photo_info.csv'), ','
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
                os.path.join(self.form.paths['project_dir'], 'tree_info.csv'), ','
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
            os.path.join(self.form.paths['project_dir'], 'panoramas')
        )
        self.lidar_window = LidarWindow()

        self.photo_window.on_change_site_requested = self.change_site
        self.photo_window.gl_widget.new_camera_direction.connect(
            self.lidar_window.update_camera_direction
        )
        self.photo_window.gl_widget.new_pointer_direction.connect(
            self.photo_window.map_widget.pointer.rotate_pointer
        )
        self.photo_window.map_widget.new_camera_position.connect(
            self.lidar_window.update_camera_position
        )
        self.photo_window.map_widget.new_panorama.connect(
            self.photo_window.gl_widget.load_image
        )
        self.photo_window.map_widget.new_tree_attributes.connect(
            self.photo_window.propriety_widget.load_data
        )
        self.lidar_window.lidar_tree_selected.connect(
            self.photo_window.map_widget.find_point
        )
        self.photo_window.map_widget.map_tree_selected.connect(
            self.lidar_window.on_map_selected_tree
        )

        self.lidar_window.show()
        overlay = show_overlay(
            self.lidar_window.centralWidget(),
            "Chargement des nuages de points…",
        )
        QApplication.processEvents()

        self.lidar_window.load_point_cloud(
            os.path.join(self.form.paths['project_dir'], 'cloud.laz'), 'main_cloud'
        )
        QApplication.processEvents()
        if self.tree_info:
            self.lidar_window.add_trees(self.tree_info)
        QApplication.processEvents()
        self.lidar_window.load_point_cloud(
            os.path.join(self.form.paths['project_dir'], 'aero_cloud.laz'), 'aeroporté'
        )
        QApplication.processEvents()

        overlay.dismiss()
        self.photo_window.show()

    def change_site(self):
        """Demande confirmation, ferme les fenêtres de navigation et retourne au choix du projet."""
        mb = QMessageBox(self.photo_window)
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
        self.lidar_window.close()
        self.photo_window.close()

        self.form.show()
        self.form.raise_()
        self.form.activateWindow()
        result = self.form.exec()
        if result != QDialog.DialogCode.Accepted:
            return
        self._open_navigation()
