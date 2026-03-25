import math
import random

import laspy as lp
import numpy as np
from pyvista import get_reader
import pyvistaqt as pvqt
from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication, QMainWindow

from forest_view.logger import get_logger

logger = get_logger(__name__)

TREE_LABEL_FONT_SIZE = 24


class LidarWindow(QMainWindow):
    camera_parameters = [[0, 0, 0], [1, 0, 0], [0, 0, 1]]
    translation = None
    lidar_tree_selected = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle('UdeS Forest View 3D')
        self.setGeometry(100, 100, 800, 600)

        self.plotter = pvqt.QtInteractor(self)
        self.setCentralWidget(self.plotter.interactor)
        self.plotter.interactor.installEventFilter(self)
        self._lidar_saved_cursor = None

        self.plotter.set_viewup([0, 0, 1])
        self.plotter.camera.view_angle = 90
        self.view_depth = 15

        self.plotter.enable_point_picking(
            callback=self.on_lidar_selected_tree, show_point=False, show_message=False
        )
        self.plotter.enable_eye_dome_lighting()
        self.plotter.add_on_render_callback(self.on_render)

    def load_point_cloud(self, point_cloud_path, actor_name):
        try:
            color = ['red', 'orangered', 'cadmiumlemon', 'limegreen', 'mediumturquoise', 'royalblue', 'mediumorchid', 'deeppink']
            las = lp.read(point_cloud_path)
            pcd = np.vstack((las.x, las.y, las.z)).transpose()
            if self.translation is None:
                self.translation = np.mean(pcd, axis=0)
            centered_pcd = pcd - self.translation
            actor = self.plotter.add_mesh(
                centered_pcd, name=actor_name, style='points', point_size=2,
                label=actor_name, pickable=False , color=random.choice(color)
            )
            if not hasattr(self, 'cloud_group'):
                self.cloud_group = []
            self.cloud_group.append(actor)
        except FileNotFoundError:
            print(f'Le fichier {point_cloud_path} n\'a pas été trouvé')
            logger.info(f'Le fichier {point_cloud_path} n\'a pas été trouvé')

    def add_trees(self, tree_data):
        if tree_data is None:
            return
        tree_pcd = np.vstack((
            [entry['x'] for entry in tree_data],
            [entry['y'] for entry in tree_data],
            [entry['z'] for entry in tree_data]
        )).transpose()
        tree_pcd = np.array(tree_pcd, dtype=float)
        if self.translation is None:
            self.translation = np.mean(tree_pcd, axis=0)
        tree_pcd = tree_pcd - self.translation
        self._tree_positions_centered = np.asarray(tree_pcd)
        self._tree_labels = [str(entry.get('No_tige', '')) for entry in tree_data]
        self.plotter.add_point_labels(
            tree_pcd, self._tree_labels, name='arbres', point_size=30, point_color='pink',
            font_size=TREE_LABEL_FONT_SIZE, always_visible=True, pickable=True
        )

    def add_qsm(self, qsm_path, actor_name):
        try:
            reader = get_reader(qsm_path)
            mesh = reader.read()
            if self.translation is None:
                self.translation = np.asarray(mesh.center)
            mesh = mesh.translate(-self.translation)
            actor = self.plotter.add_mesh(mesh, name=actor_name, pickable=False)
            if not hasattr(self, 'qsm_group'):
                self.qsm_group = []
            self.qsm_group.append(actor)
        except FileNotFoundError:
            print(f'Le fichier {qsm_path} n\'a pas été trouvé')
            logger.info(f'Le fichier {qsm_path} n\'a pas été trouvé')

    def set_visibility(self, group, state):
        if group == 'qsm' and hasattr(self, 'qsm_group'):
            for item in self.qsm_group:
                item.visibility = state
        elif group == 'cloud' and hasattr(self, 'cloud_group'):
            for item in self.cloud_group:
                item.visibility = state
        else:
            pass

    def update_camera_position(self, camera_position):
        if len(self.plotter.actors) != 0:
            centered_position = camera_position - self.translation
            self.camera_parameters[1] = list(
                np.array(self.camera_parameters[1])
                - (np.array(self.camera_parameters[0]) - np.array(centered_position))
            )
            self.camera_parameters[0] = list(centered_position)
            self.plotter.camera_position = self.camera_parameters
            self._update_render_view_depth(self.view_depth)
        else:
            pass

    def update_camera_direction(self, camera_direction, yaw=0):
        if camera_direction[2] == 1:
            self.camera_parameters[2] = [-math.sin(yaw), -math.cos(yaw), 0]
        elif camera_direction[2] == -1:
            self.camera_parameters[2] = [math.sin(yaw), math.cos(yaw), 0]
        else:
            self.camera_parameters[2] = [0, 0, 1]
        self.camera_parameters[1] = list(np.array(self.camera_parameters[0]) + np.array(camera_direction))
        self.plotter.camera_position = self.camera_parameters
        self._update_render_view_depth(self.view_depth)

    def _update_render_view_depth(self, view_depth):
        self.view_depth = view_depth
        try:
            d = self.camera_parameters[1][2] - self.camera_parameters[0][2]
            z_norm = math.cos(math.atan(d / math.sqrt(d**2 + d**2)))
        except (ZeroDivisionError, TypeError):
            z_norm = 0.001
        self.plotter.camera.clipping_range = (0.5, self.view_depth / (1.1 - abs(z_norm)**3))

    def on_render(self, plotter):
        self.camera_parameters = [list(bloc) for bloc in self.plotter.camera_position]
        self._update_render_view_depth(self.view_depth)

    def eventFilter(self, obj, event):
        if obj is self.plotter.interactor:
            if event.type() == QEvent.Type.MouseButtonPress:
                self._lidar_saved_cursor = self.plotter.interactor.cursor()
                self.plotter.interactor.setCursor(QCursor(Qt.CursorShape.WaitCursor))
            elif event.type() == QEvent.Type.MouseButtonRelease:
                cursor = self._lidar_saved_cursor or QCursor(Qt.CursorShape.ArrowCursor)
                self.plotter.interactor.setCursor(cursor)
        return super().eventFilter(obj, event)

    def on_lidar_selected_tree(self, picked_point):
        if 'selected_point' in self.plotter.actors.keys():
            self.plotter.remove_actor('selected_point')
        picked_centered = np.asarray(picked_point)
        self.plotter.add_mesh(picked_centered, name='selected_point', point_size=30, color='yellow')
        self._highlight_selected_label(picked_centered)
        picked_point = np.array(picked_point) + self.translation
        self.lidar_tree_selected.emit(picked_point)
        
    def on_map_selected_tree(self, tree_position):
        if 'selected_point' in self.plotter.actors.keys():
            self.plotter.remove_actor('selected_point')
        tree_position = np.asarray(tree_position, dtype=float)
        tree_position_centered = tree_position - self.translation
        self.plotter.add_mesh(tree_position_centered, name='selected_point', point_size=30, color='yellow')
        self._highlight_selected_label(tree_position_centered)

    def _highlight_selected_label(self, position_centered):
        """Affiche le libellé (No_tige) de l'arbre sélectionné en surbrillance dans le nuage de points."""
        if not hasattr(self, '_tree_positions_centered') or self._tree_positions_centered is None:
            return
        if not hasattr(self, '_tree_labels') or not self._tree_labels:
            return
        pos = np.asarray(position_centered).reshape(1, 3)
        dists = np.linalg.norm(self._tree_positions_centered - pos, axis=1)
        idx = int(np.argmin(dists))
        label = self._tree_labels[idx]
        if 'selected_label' in self.plotter.actors.keys():
            self.plotter.remove_actor('selected_label')
        self.plotter.add_point_labels(
            self._tree_positions_centered[idx : idx + 1],
            [label],
            name='selected_label',
            point_size=0,
            font_size=TREE_LABEL_FONT_SIZE,
            text_color='yellow',
            bold=True,
            always_visible=True,
        )

    def change_site(self, cloud_path, tree_info):
        self.reset()
        self.load_point_cloud(cloud_path, 'main_cloud')
        if tree_info is not None:
            self.add_trees(tree_info)

    def reset(self):
        self.plotter.clear_actors()
        self.camera_parameters = [[0, 0, 0], [1, 0, 0], [0, 0, 1]]
        self.plotter.camera_position = self.camera_parameters
        self.translation = None
        self._tree_positions_centered = None
        self._tree_labels = None

    def closeEvent(self, event):
        self.plotter.close()
        super().closeEvent(event)
        if not getattr(self, '_returning_to_project_selection', False):
            QApplication.quit()
