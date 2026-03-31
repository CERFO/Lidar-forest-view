import math
import random

import laspy as lp
import numpy as np
from pyvista import get_reader
import pyvistaqt as pvqt
from PyQt6.QtCore import QEvent, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMainWindow

from forest_view.logger import get_logger

logger = get_logger(__name__)

TREE_LABEL_FONT_SIZE = 24


class LidarWindow(QMainWindow):
    lidar_tree_selected = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle('UdeS Forest View 3D')
        self.setGeometry(100, 100, 800, 600)

        self.plotter = pvqt.QtInteractor(self)
        self.setCentralWidget(self.plotter.interactor)
        self.plotter.interactor.installEventFilter(self)

        self.plotter.set_viewup([0, 0, 1])
        self.plotter.camera.view_angle = 90
        self.view_depth = 15

        self.plotter.enable_point_picking(
            callback=self.on_lidar_selected_tree, show_point=False, show_message=False
        )
        self.plotter.enable_eye_dome_lighting()
        self.plotter.add_on_render_callback(self.on_render)
        self.camera_parameters = [[0, 0, 0], [1, 0, 0], [0, 0, 1]]
        self.translation = None
        self.cloud_group = []
        self.qsm_group = []
        self.point_size = 1.0
        self.point_size_min = 1.0
        self.point_size_max = 10.0
        self.adaptive_point_size = False
        self.adaptive_max_depth = 5.0
        self._applied_point_size = None
        self._aligned_camera_parameters = None
        self.lock_world_up = True
        self.point_color = None

    def load_point_cloud(self, point_cloud_path, actor_name):
        try:
            color = ['red', 'orangered', 'cadmiumlemon', 'limegreen', 'mediumturquoise', 'royalblue', 'mediumorchid', 'deeppink']
            las = lp.read(point_cloud_path)
            pcd = np.vstack((las.x, las.y, las.z)).transpose()
            if self.translation is None:
                self.translation = np.mean(pcd, axis=0)
            centered_pcd = pcd - self.translation
            mesh_color = self.point_color if self.point_color is not None else random.choice(color)
            actor = self.plotter.add_mesh(
                centered_pcd, name=actor_name, style='points', point_size=self.point_size,
                label=actor_name, pickable=False, color=mesh_color
            )
            self.cloud_group.append(actor)
            self._apply_cloud_point_size(self._compute_current_point_size())
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
            self.qsm_group.append(actor)
        except FileNotFoundError:
            print(f'Le fichier {qsm_path} n\'a pas été trouvé')
            logger.info(f'Le fichier {qsm_path} n\'a pas été trouvé')

    def set_visibility(self, group, state):
        if group == 'qsm':
            for item in self.qsm_group:
                item.visibility = state
        elif group == 'cloud':
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
            self._save_aligned_camera_parameters()
        else:
            pass

    def update_camera_direction(self, camera_direction, yaw=0):
        if self.lock_world_up:
            self.camera_parameters[2] = [0, 0, 1]
        elif camera_direction[2] == 1:
            self.camera_parameters[2] = [-math.sin(yaw), -math.cos(yaw), 0]
        elif camera_direction[2] == -1:
            self.camera_parameters[2] = [math.sin(yaw), math.cos(yaw), 0]
        else:
            self.camera_parameters[2] = [0, 0, 1]
        self.camera_parameters[1] = list(np.array(self.camera_parameters[0]) + np.array(camera_direction))
        self.plotter.camera_position = self.camera_parameters
        if self.lock_world_up:
            self._enforce_world_up()
        self._update_render_view_depth(self.view_depth)
        self._save_aligned_camera_parameters()

    def _update_render_view_depth(self, view_depth):
        self.view_depth = view_depth
        try:
            d = self.camera_parameters[1][2] - self.camera_parameters[0][2]
            z_norm = math.cos(math.atan(d / math.sqrt(d**2 + d**2)))
        except (ZeroDivisionError, TypeError):
            z_norm = 0.001
        base_far = self.view_depth / (1.1 - abs(z_norm)**3)
        try:
            cam_pos = np.asarray(self.camera_parameters[0], dtype=float)
            focal_pos = np.asarray(self.camera_parameters[1], dtype=float)
            cam_to_focal = float(np.linalg.norm(focal_pos - cam_pos))
        except (TypeError, ValueError):
            cam_to_focal = float(self.view_depth)
        if not np.isfinite(cam_to_focal):
            cam_to_focal = float(self.view_depth)
        far_clip = max(float(base_far), cam_to_focal + (2.0 * float(self.view_depth)), 100.0)
        self.plotter.camera.clipping_range = (0.5, far_clip)

    def on_render(self, plotter):
        self.camera_parameters = [list(bloc) for bloc in self.plotter.camera_position]
        self._update_render_view_depth(self.view_depth)
        self._apply_cloud_point_size(self._compute_current_point_size())

    def _enforce_world_up(self):
        try:
            up = np.asarray(self.plotter.camera.up, dtype=float)
        except (TypeError, ValueError):
            up = np.array([0.0, 0.0, 0.0], dtype=float)
        if np.linalg.norm(up - np.array([0.0, 0.0, 1.0])) > 1e-4:
            self.plotter.camera.up = (0.0, 0.0, 1.0)

    def set_lock_world_up(self, enabled):
        self.lock_world_up = bool(enabled)
        if self.lock_world_up:
            self._enforce_world_up()
            self.camera_parameters = [list(bloc) for bloc in self.plotter.camera_position]
            self._save_aligned_camera_parameters()
        self.plotter.render()

    def _compute_current_point_size(self):
        if not self.adaptive_point_size:
            return float(self.point_size)
        try:
            cam_pos = np.asarray(self.camera_parameters[0], dtype=float)
            focal_pos = np.asarray(self.camera_parameters[1], dtype=float)
            distance = float(np.linalg.norm(focal_pos - cam_pos))
        except (TypeError, ValueError):
            distance = 0.0
        if not np.isfinite(distance) or distance <= 0.01:
            distance = 0.0

        max_depth = max(0.01, float(self.adaptive_max_depth))
        base_size = float(np.clip(self.point_size, self.point_size_min, self.point_size_max))
        near_size = 10.0
        if distance <= max_depth:
            # Courbe plus stable: la taille décroît rapidement près de la caméra,
            # sans rester "trop bold" quand la profondeur adaptative augmente.
            t = distance / max_depth
            scaled = base_size + ((near_size - base_size) * math.exp(-5.0 * t))
        else:
            scaled = base_size
        return float(np.clip(scaled, self.point_size_min, self.point_size_max))

    def _apply_cloud_point_size(self, size):
        size = float(np.clip(size, self.point_size_min, self.point_size_max))
        if self._applied_point_size is not None and abs(size - self._applied_point_size) < 0.01:
            return
        for actor in self.cloud_group:
            actor.prop.point_size = size
        self._applied_point_size = size

    def _save_aligned_camera_parameters(self):
        self._aligned_camera_parameters = [list(bloc) for bloc in self.plotter.camera_position]

    def set_point_size(self, point_size):
        self.point_size = float(np.clip(point_size, self.point_size_min, self.point_size_max))
        self._apply_cloud_point_size(self._compute_current_point_size())
        self.plotter.render()

    def set_point_color(self, color_rgb):
        if color_rgb is None:
            return
        r, g, b = color_rgb
        self.point_color = (
            float(np.clip(r, 0.0, 1.0)),
            float(np.clip(g, 0.0, 1.0)),
            float(np.clip(b, 0.0, 1.0)),
        )
        for actor in self.cloud_group:
            actor.prop.color = self.point_color
        self.plotter.render()

    def set_adaptive_point_size(self, enabled):
        self.adaptive_point_size = bool(enabled)
        self._apply_cloud_point_size(self._compute_current_point_size())
        self.plotter.render()

    def set_adaptive_max_depth(self, max_depth):
        self.adaptive_max_depth = max(1.0, float(max_depth))
        self._apply_cloud_point_size(self._compute_current_point_size())
        self.plotter.render()

    def set_forward_view_from_yaw(self, yaw):
        if len(self.plotter.actors) == 0:
            return
        pos = np.asarray(self.camera_parameters[0], dtype=float)
        direction = np.array([math.sin(yaw), math.cos(yaw), 0.0], dtype=float)
        if np.linalg.norm(direction) < 1e-9:
            direction = np.array([1.0, 0.0, 0.0], dtype=float)
        self.camera_parameters[2] = [0, 0, 1]
        self.camera_parameters[1] = list(pos + direction)
        self.plotter.camera_position = self.camera_parameters
        self._update_render_view_depth(self.view_depth)
        self._save_aligned_camera_parameters()
        self.plotter.render()

    def reset_view(self):
        if len(self.plotter.actors) == 0:
            return
        if self._aligned_camera_parameters is not None:
            self.camera_parameters = [list(bloc) for bloc in self._aligned_camera_parameters]
            self.plotter.camera_position = self.camera_parameters
        else:
            bounds = self.plotter.bounds
            if bounds is None or len(bounds) != 6:
                self.camera_parameters = [[0, -30, 10], [0, 0, 0], [0, 0, 1]]
                self.plotter.camera_position = self.camera_parameters
            else:
                xmin, xmax, ymin, ymax, zmin, zmax = [float(v) for v in bounds]
                cx = (xmin + xmax) / 2.0
                cy = (ymin + ymax) / 2.0
                cz = (zmin + zmax) / 2.0
                dx = max(1.0, xmax - xmin)
                dy = max(1.0, ymax - ymin)
                dz = max(1.0, zmax - zmin)
                radius = 0.5 * math.sqrt(dx * dx + dy * dy + dz * dz)
                distance = max(20.0, 2.2 * radius)
                self.camera_parameters = [
                    [cx, cy - distance, cz + 0.35 * distance],
                    [cx, cy, cz],
                    [0, 0, 1],
                ]
                self.plotter.camera_position = self.camera_parameters
        self.plotter.camera.view_angle = 90
        self.camera_parameters = [list(bloc) for bloc in self.plotter.camera_position]
        self._update_render_view_depth(self.view_depth)
        self._applied_point_size = None
        self._apply_cloud_point_size(self._compute_current_point_size())
        self.plotter.render()

    def eventFilter(self, obj, event):
        if obj is self.plotter.interactor:
            if event.type() == QEvent.Type.MouseButtonRelease:
                if self.lock_world_up:
                    self._enforce_world_up()
                    self.plotter.render()
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

    def delete_tree(self, tree_position):
        """ Retire le point d'arbre à la position fournie"""
        tree_position_centered = tree_position - self.translation
        for i, tree in enumerate(self._tree_positions_centered):
            if all(tree == tree_position_centered):
                self._tree_positions_centered = np.delete(self._tree_positions_centered, i, axis = 0)
                del self._tree_labels[i]
                break
        self.plotter.add_point_labels(
            self._tree_positions_centered, self._tree_labels, name='arbres', point_size=30, point_color='pink',
            font_size=TREE_LABEL_FONT_SIZE, always_visible=True, pickable=True
        )

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
        self.cloud_group = []
        self.qsm_group = []
        self._applied_point_size = None
        self._aligned_camera_parameters = None
        self.translation = None
        self._tree_positions_centered = None
        self._tree_labels = None

    def closeEvent(self, event):
        self.plotter.close()
        super().closeEvent(event)
        if not getattr(self, '_returning_to_project_selection', False):
            QApplication.quit()
