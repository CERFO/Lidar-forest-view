import math

import laspy as lp
import numpy as np
import pyvistaqt as pvqt
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QMainWindow


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

        self.plotter.set_viewup([0, 0, 1])
        self.plotter.camera.view_angle = 90
        self.view_depth = 15

        self.plotter.enable_point_picking(
            callback=self.point_picked, color='yellow', point_size=30, show_message=False
        )
        self.plotter.enable_eye_dome_lighting()
        self.plotter.enable_fly_to_right_click()
        self.plotter.add_on_render_callback(self.on_render)

    def load_point_cloud(self, point_cloud_path, actor_name):
        try:
            las = lp.read(point_cloud_path)
            pcd = np.vstack((las.x, las.y, las.z)).transpose()
            if self.translation is None:
                self.translation = np.mean(pcd, axis=0)
            centered_pcd = pcd - self.translation
            self.plotter.add_mesh(
                centered_pcd, name=actor_name, style='points', point_size=2,
                label=actor_name, pickable=False
            )
        except FileNotFoundError:
            print(f'Le fichier {point_cloud_path} n\'a pas été trouvé')

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
        labels = [entry['No_tige'] for entry in tree_data]
        self.plotter.add_point_labels(
            tree_pcd, labels, name='arbres', point_size=30, point_color='pink',
            always_visible=True, pickable=True
        )

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

    def update_camera_direction(self, camera_direction):
        if camera_direction[2] == 1:
            self.camera_parameters[2] = [0, 1, 0]
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

    def point_picked(self, picked_point):
        picked_point = np.array(picked_point) + self.translation
        self.lidar_tree_selected.emit(picked_point)

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

    def closeEvent(self, event):
        self.plotter.close()
        super().closeEvent(event)
