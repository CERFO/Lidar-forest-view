import os
import sys
import csv
import json
import math
import subprocess
from collections import defaultdict
import laspy as lp
import numpy as np
import open3d as o3d
from PIL import Image
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtOpenGL import QGLWidget

class DataForm(QDialog):
    '''
    Formulaire de saisie de chemins d'accès vers des fichiers ou des répertoires.

    Args :
        fields (list) : Liste de tuples contenant le texte du label, le nom du champ et le type de chemin ('file' ou 'répertoire').
        title (str) : Titre de la fenêtre du formulaire.
    '''
    def __init__(self, fields, title="Saisie des chemins d'accès"):
        super().__init__()
        self.setWindowTitle(title)

        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.Dialog)

        self.fields = {}
        self.paths = {}
        self.memory = readJSON('memory.json') if os.path.exists('memory.json') else {}

        self.layout = QFormLayout()

        # Ajoute les champs de saisie
        for text, field, type in fields:
            self.add_field(text, field, type)

        # Bouton de soumission
        self.submit_button = QPushButton("Soumettre")
        self.submit_button.clicked.connect(self.submit_data)
        
        self.layout.addRow(self.submit_button)

        self.setLayout(self.layout)

    def add_field(self, label_text, field_name, path_type):
        '''Ajout un champ de saisie avec un label et un bouton de navigation
        Args:
            label_text (str): Texte du label pour le champ de saisie.
            field_name (str): Nom du champ de saisie, utilisé pour stocker la valeur dans self.paths.
            path_type (str): Type de chemin ('file' ou 'répertoire').'''
        
        inner_layout = QHBoxLayout()
        line_edit = QLineEdit(text = self.memory[field_name] if field_name in self.memory else '')
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(lambda _, le=line_edit: self.browse_file(le, label_text, path_type))

        inner_layout.addWidget(line_edit)
        inner_layout.addWidget(browse_button)

        self.layout.addRow(label_text, inner_layout)
        self.fields[field_name] = line_edit

    def browse_file(self, line_edit, caption, path_type):
        '''Ouvre une boîte de dialogue pour sélectionner un fichier ou un répertoire'''
        if path_type == 'file':
            file_path, _ = QFileDialog.getOpenFileName(self, f'Sélectionnez {caption}') # TODO : ajouter un filtre pour les fichiers (requiert un argument supplémentaire)
        elif path_type == 'répertoire':
            file_path = QFileDialog.getExistingDirectory(self, f'Sélectionnz {caption}')

        if file_path:
            line_edit.setText(file_path)

    def submit_data(self):
        '''Valide les champs et enregistre les chemins dans self.paths et self.memory, puis crée un fichier JSON de mémoire'''
        self.paths.clear()
        if all(value.text() != '' for value in self.fields.values()):
            for field_name, line_edit in self.fields.items():
                self.paths[field_name] = line_edit.text()
                if field_name in self.memory:
                    self.memory[field_name] = line_edit.text()
                else:
                    self.memory.update({field_name: line_edit.text()})
            writeJSON('memory.json', self.memory)
            self.close()
        else:
            QMessageBox.warning(self, 'Champs incomplets', 
                                'Tous les champs doivent être remplis pour soumettre')
            
    def closeEvent(self, event):
        '''Gère la fermeture de la fenêtre par le «X» et arrète le programme'''
        if self.paths != {} and all(value != '' for value in self.paths.values()):
            event.accept()
        else:
            # Show a message box to inform the user
            reply = QMessageBox.question(self, 'Vous partez déjà?',
                                       'Êtes-vous sûr de vouloir quitter?',
                                       QMessageBox.Yes | QMessageBox.No,
                                       QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                event.accept()  # Accept the close event first
                sys.exit()  # Force la sortie
            else:
                event.ignore()  # Prevent the dialog from closing

class GLWidget(QGLWidget):
    new_camera_direction = pyqtSignal(object)
    new_pointer_direction = pyqtSignal(float)
    '''
    Visionneuse de photos 3D (Équirectangulaire) utilisant OpenGL

    Args:
        parent (QWidget): Le widget parent dans lequel le GLWidget sera intégré.
    '''
    def __init__(self, parent, photo_dir):
        super().__init__(parent)
        self.image = Image.new('RGB', (100, 50), color='gray')
        self.image_width, self.image_height = self.image.size
        self.yaw = 0
        self.pitch = 0
        self.prev_dx = 0
        self.prev_dy = 0
        self.fov = 90
        self.moving = False
        self.image_yaw = 0
        self.image_pitch = 0
        self.image_roll = 0
        self.main_window = parent
        self.photo_dir = photo_dir

    def load_image(self, image_path, image_yaw=0, image_pitch=0, image_roll=0):
        """Load a new panorama image"""
        if image_path:
            try:
                self.image = Image.open(os.path.join(self.photo_dir, image_path))
                self.image_width, self.image_height = self.image.size
                # Refresh the texture if OpenGL is already initialized
                if hasattr(self, 'texture'):
                    self.update_texture()
                self.yaw -= (image_yaw - self.image_yaw)        # pourrait être modifié pour devenir les angles absolues
                self.pitch -= (image_pitch - self.image_pitch)  #les corrections pour l'image peuvent se faire dans paintGL
                self.image_yaw = image_yaw
                self.image_pitch = image_pitch
                self.image_roll = image_roll
                self.update()  # Enclanche un repaint
                print(f"Loaded image: {image_path}")
            except Exception as e:
                print(f"Error loading image {image_path}: {e}")
        else:
            self.image = Image.new('RGB', (100, 50), color='gray')
            self.image_width, self.image_height = self.image.size
                # Refresh the texture if OpenGL is already initialized
            if hasattr(self, 'texture'):
                self.update_texture()
                self.yaw = 0
                self.image_yaw = 0
                self.update()  # Trigger repaint
                print(f"Loaded image: {image_path}")

    def update_texture(self):
        """Update OpenGL texture with current image"""
        self.makeCurrent()
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, self.image_width, self.image_height, 0, GL_RGB, GL_UNSIGNED_BYTE, self.image.tobytes())
        self.doneCurrent()

    def initializeGL(self):
        glEnable(GL_TEXTURE_2D)
        self.texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, self.image_width, self.image_height, 0, GL_RGB, GL_UNSIGNED_BYTE, self.image.tobytes())
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        self.sphere = gluNewQuadric()
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(90, self.width()/self.height(), 0.1, 1000) # Field of view au premier argument
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glPushMatrix()
        glRotatef(-self.image_roll, 0, 0, 1)
        glRotatef(self.pitch, 1, 0, 0)
        glRotatef(self.yaw, 0, 1, 0)
        glRotatef(90, 1, 0, 0)
        # glRotatef(-90, 0, 0, 1) # Pour des images gauche droite plutôt que avant-arrière
        gluQuadricTexture(self.sphere, True)
        gluSphere(self.sphere, 1, 100, 100)
        glPopMatrix()
          
    def resizeGL(self, width, height):
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(self.fov, self.width()/self.height(), 0.1, 1000)

    def reset(self):
        self.yaw = 0
        self.pitch = 0
        self.image_yaw = 0
        self.image_pitch = 0
        self.image_roll = 0
        self.load_image(None)
        self.photo_dir = None
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_x, self.mouse_y = event.pos().x(), event.pos().y()
            self.moving = True

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.moving = False

        # met à jour la direction de la caméra
        roll, pitch, yaw = math.radians(self.image_roll), math.radians(self.image_pitch + self.pitch), math.radians(self.image_yaw + self.yaw)
        camera_direction = np.array([math.cos(pitch) * math.sin(yaw), math.cos(pitch) * math.cos(yaw), -math.sin(pitch)])
        self.new_camera_direction.emit(camera_direction)

    def mouseMoveEvent(self, event):
        if self.moving:
            dx = event.pos().x() - self.mouse_x 
            dy = event.pos().y() - self.mouse_y
            dx *= 0.1
            dy *= 0.1
            self.yaw += dx
            self.pitch += dy
            self.pitch = min(max(self.pitch, -90), 90)
            self.mouse_x, self.mouse_y = event.pos().x(), event.pos().y()
            self.update()

            # Gère la rotation du pointeur
            self.new_pointer_direction.emit(self.image_yaw + self.yaw)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        self.fov -= delta * 0.1
        self.fov = max(30, min(self.fov, 90))
        self.makeCurrent()
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(self.fov, self.width()/self.height(), 0.1, 1000)
        self.doneCurrent()
        self.update()

class CustomMapWidget(QGraphicsView):
    new_camera_position = pyqtSignal(object)
    new_pointer_position = pyqtSignal(object)
    new_panorama = pyqtSignal(str, float, float, float)
    new_tree_attributes = pyqtSignal(object)
    last_selection = []
    '''
    Carte de points d'intérêt

    Args:
        photo_coordinates (dict): Données et coordonnées à afficher.
        main_window (QWidget, optional): Référence à la fenêtre principale pour interagir avec d'autres composants.
        tree_coordinates (dict, optional): Données et coordonnées d'arbres à afficher.
    '''
    def __init__(self, photo_coordinates, tree_coordinates = None):
        super().__init__()
        self.scene = QGraphicsScene()
        self.scene.selectionChanged.connect(self.on_selection_change)
        self.setScene(self.scene)
        self.setMinimumSize(100, 100)
        self.setBackgroundBrush(QColor(200, 200, 200))  # Set a light gray background
        
        # conversion des coordonées de la scène et ajout des points
        self.plot_photo_coordinates(photo_coordinates)

        if tree_coordinates is not None: # TODO
            self.plot_tree_coordinates(tree_coordinates)

        # Permet la manipulation de la carte
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setRenderHint(QPainter.Antialiasing)
        # Ajustement de la vue aux points ajoutés
        self.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
        self.scene.setSceneRect(self.scene.itemsBoundingRect().marginsAdded(QMarginsF(10,10,10,10)))
        self.create_pointer()
    
    def plot_photo_coordinates(self, photo_coordinates):
        '''Affiche les points de photos sur la carte.
        Args: photo_coordinates (list): Liste de dictionnaires contenant les informations des photos.'''

        if not photo_coordinates:
            return
        
        # Plot points
        for entry in photo_coordinates:
            # Convertion en coordonnées de scène
            path = entry['image']
            scene_x = float(entry['x'])
            scene_y = -float(entry['y'])  # Inverser Y pour correspondre à la scène Qt
            scene_z = float(entry['z'])   # Ajouter la coordonnée Z si disponible
            yaw = float(entry['yaw']) if 'yaw' in entry else 0  # Ajouter le yaw si disponible
            pitch = float(entry['pitch']) if 'pitch' in entry else 0  # Ajouter le pitch si disponible
            roll = float(entry['roll']) if 'roll' in entry else 0  # Ajouter le roll si disponible

            # Ajout du point à la scène
            point = PhotoPoint(path, scene_x, scene_y, scene_z, yaw, pitch, roll, self, 10)
            self.scene.addItem(point)

    def plot_tree_coordinates(self, tree_coordinates): # TODO
        '''Affiche les points d'arbres sur la carte.'
        Args: tree_coordinates (list): Liste de dictionnaires contenant les informations des arbres.'''
        
        if not tree_coordinates:
            return
        
        # Plot points
        for entry in tree_coordinates:
            # Convertion en coordonnées de scène
            scene_x = float(entry['x'])
            scene_y = -float(entry['y'])  # Inverser Y pour correspondre à la scène Qt
            tree_data = {k: v for k,v in entry.items() if k not in {'x', 'y', 'z'}}  
            
            # Ajout du point à la scène
            point = TreePoint(scene_x, scene_y, tree_data, self, 10)
            self.scene.addItem(point)

    def create_pointer(self):
        # Crée un pointeur dans la scène
        if not hasattr(self, 'pointer') or self.pointer is None:
            self.pointer = Pointer()
            self.scene.addItem(self.pointer)
            self.new_pointer_position.connect(self.pointer.setPos)

    def reset(self):
        self.new_pointer_position.disconnect()
        self.scene.clear()
        self.pointer = None
        self.create_pointer()
        self.new_pointer_position.connect(self.pointer.setPos)

        self.last_selection = []
        self.scene.clearSelection()

    def wheelEvent(self, event):
        #Gère le zoom de la carte
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

    def find_point(self, position): # TODO essayer de trouver une autre solution : pas très propre
        x = position[0]
        y = -position[1]
        items = self.scene.items(QPointF(x, y))
        for item in items:
            if isinstance(item, TreePoint):
                if item.pos() == QPointF(x, y):
                    tree = item
                    self.last_selection = []
                    self.scene.clearSelection()
                    item.setSelected(True)
                    self.new_tree_attributes.emit(tree.tree_data)
                    break

class ProprietyWidget(QWidget):
    '''
    Widget de propriétés pour afficher les informations des points d'intérêt.

    Args:
        Fields (list): Liste de champs à afficher dans le widget de propriétés.
    '''
    def __init__(self, fields):
        super().__init__()
        self.inner_layout = QFormLayout()
        self.inner_layout.setLabelAlignment(Qt.AlignRight)
        self.inner_layout.setFormAlignment(Qt.AlignLeft)

        # font = QFont()
        # font.setPointSize(9)

        self.set_fields(fields)

        self.setLayout(self.inner_layout)

    def set_fields(self, fields):
        for field in fields:
            label = QLabel(f'{field} :')
            # label.setFont(font)
            attribute = QLabel('')
            # attribute.setFont(font)
            self.inner_layout.addRow(label, attribute)
           
    def load_data(self, data): # TODO: Modifier selon la structure choisie des données des arbres
        # Charge les données dans le widget de propriétés
        for i in range(self.inner_layout.rowCount()):
            label = self.inner_layout.itemAt(i, QFormLayout.LabelRole).widget().text()[0:-2]  # Enlève le " :"
            if label in data.keys():
                self.inner_layout.itemAt(i, QFormLayout.FieldRole).widget().setText(str(data[label]))
            else:
                self.inner_layout.itemAt(i, QFormLayout.FieldRole).widget().setText('ND')

    def reset(self):
        for i in range(self.inner_layout.rowCount()):
            self.inner_layout.removeRow(0)

class Open3DViewer():
    """
    Visionneuse de nuages de points 3D utilisant Open3D
    
    Args:
        shared (SharedData): Instance de SharedData pour partager les données entre les threads.
    """
    def __init__(self, shared):
        self.app = o3d.visualization.gui.Application.instance
        self.app.initialize()

        self.window = o3d.visualization.gui.Application.instance.create_window("UdeS Forest View 3D", 800, 600, 30, 30)
        self.scene = o3d.visualization.gui.SceneWidget()
        self.scene.scene = o3d.visualization.rendering.Open3DScene(self.window.renderer)
        self.window.add_child(self.scene)

        # self.scene.scene.show_axes(True)
        # self.scene.scene.show_ground_plane(True, rendering.Scene.GroundPlane(1))
        self.scene.set_view_controls(o3d.visualization.gui.SceneWidget.Controls.FLY) # ROTATE_CAMERA est bien aussi

        self.shared = shared
        self.center = [0, 0, 0]
        self.material = o3d.visualization.rendering.MaterialRecord()
        self.material.shader = "depth"

        # self.scene.scene.scene.add_point_light('self_light', [1, 1, 1], [0, 0, 0], 255.0, 1.0, False)

        self.window.set_on_tick_event(self.on_tick)

    def on_tick(self):
        '''Gère les mises à jour de la scène'''
        with self.shared.lock:
            # if not self.shared.running: # Vérifie si l'application est en cours d'exécution : utile si on utilise l'index 0 dans la visionneuse
            #     self.app.quit()

            if self.shared.cloud_updated:
                self.update_cloud(self.shared.cloud_path)
                self.shared.cloud_updated = False
                print("Cloud updated")

            if self.shared.updated:
                print('trying to update camera position')
                self.update_camera_position(self.shared.camera_position, self.shared.camera_direction)
                self.shared.updated = False
                print("Camera position updated")

    def update_cloud(self, cloud_path):
        '''Met à jour le nuage de points du projet'''
        try:
            las = lp.read(cloud_path)
            print('Loaded')

            total_pts = las.header.point_count
            decimation_factor = 3 # Facteur de décimation
            decimated_indices = np.arange(0, total_pts, decimation_factor)
            decimated_las = las.points[decimated_indices]
            print('Decimated')

            points = np.vstack((decimated_las.x, decimated_las.y, decimated_las.z)).transpose()
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(points)
            self.center = pcd.get_center()
            self.centered_pcd = pcd.translate(-pcd.get_center())
            print('Centered')

            if self.scene.scene.has_geometry('Point Cloud'):
                self.scene.scene.remove_geometry('Point Cloud')

            self.scene.scene.add_geometry("Point Cloud", self.centered_pcd, material=self.material)

        except FileNotFoundError:
            print(f"Le fichier n'a pas été trouvé: {cloud_path}")
        except Exception as e:
            print(f"Erreur lors de la mise à jour du nuage: {e}")

    def update_camera_position(self, camera_position, camera_direction):
        ''' Met à jour la position et la direction de la caméra dans la scène
            Découpe le nuage de points en fonction de la position de la caméra

        Args : camera_position (tuple): Un tuple contenant les coordonnées (x, y, z) de la position de la caméra
                camera_direction (tuple): Un tuple contenant les angles (roll, pitch, yaw) de la direction de la caméra'''
        
        # Direction de vue
        roll, pitch, yaw = [math.radians(angle) for angle in camera_direction]  # Convertit les angles en radians

        # Détermine la position de la caméra (eye) et la cible (center)
        eye = camera_position - self.center
        center = eye + np.array([math.cos(pitch) * math.sin(yaw), math.cos(pitch) * math.cos(yaw), -math.sin(pitch)])

        self.scene.look_at(center, eye, [0, 0, 1])

        if self.scene.scene.has_geometry('Point Cloud'):
            self.scene.scene.remove_geometry('Point Cloud')
    
        # Découpe le nuage de points autour de la position de la caméra
        size = 15
        bounding_box = o3d.geometry.AxisAlignedBoundingBox(min_bound=np.array([eye[0] - size, eye[1] - size, -100]), max_bound=np.array([eye[0] + size, eye[1] + size, 100]))
        cropped_cloud = self.centered_pcd.crop(bounding_box)

        self.scene.scene.add_geometry("Point Cloud", cropped_cloud, material=self.material)

        # self.scene.scene.scene.update_light_position('self_light', eye) # Pour ajouter un éclairage : pas nécessaire avec la visionneuse actuelle

class PhotoPoint(QGraphicsEllipseItem):
    '''
    Point interactif pour les photos à afficher sur la carte.

    Args :
        path (str): Chemin de l'image associée au point.
        x (float): Position X du point dans la scène.
        y (float): Position Y du point dans la scène.
        z (float): Position Z du point (altitude).
        yaw (float): Orientation du point en degrés.
        pitch (float): Inclinaison du point en degrés.
        roll (float): Roulis du point en degrés.
        main_window (QWidget, optional): Référence à la fenêtre principale pour interagir avec d'autres composants.
        size (int, optional): Taille du point. Par défaut, 10.
    '''
    def __init__(self, path, x, y, z, yaw=0, pitch=0, roll=0, parent=None, size=10):
        super().__init__(-size/2, -size/2, size, size)
        self.setBrush(Qt.blue)
        self.setPos(x, y)
        self.setCursor(Qt.ArrowCursor)  # Set cursor to arrow for better UX
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)  # Ignore transformations to keep the point size constant

        self.path = path
        self.z = z
        self.yaw = 90 - yaw  # Ajustement de l'orientation pour correspondre à la vue OpenGL # TODO vérifier si la correction est la même pour le Eagle
        self.pitch = pitch                                                                          # Si ce n'est pas le cas, corriger à la création des csv
        self.roll = roll
        self.parent = parent  # Référence au map_widget pour emetre les signaux

    def mousePressEvent(self, event):
        # Change l'image affichée dans la fenêtre principale
        if self.parent and hasattr(self.parent, 'new_panorama'):
            self.parent.new_panorama.emit(self.path, self.yaw, self.pitch, self.roll)

        # Déplace le pointeur à la position du point cliqué
        if self.parent and hasattr(self.parent, 'new_pointer_position'):
            self.parent.new_pointer_position.emit(self.pos())

        # Modifie la position de la caméra dans le nuage de points
        if self.parent and hasattr(self.parent, 'new_camera_position'):
            camera_position = np.array([self.pos().x(), -self.pos().y(), self.z])
            self.parent.new_camera_position.emit(camera_position)

        super().mousePressEvent(event)

class TreePoint(QGraphicsEllipseItem):
    '''
    Point interactif pour les arbres à afficher sur la carte.

    Args :
        x (float): Position X du point dans la scène.
        y (float): Position Y du point dans la scène.
        tree_data (dict): Données associées à l'arbre.
        main_window (QWidget, optional): Référence à la fenêtre principale pour interagir avec d'autres composants.
        size (int, optional): Taille du point. Par défaut, 10.
    '''
    def __init__(self, x, y, tree_data, parent = None, size=10): # TODO : ajouter tous les paramètres nécessaires pour l'arbre
        # size = 1 + int(tree_data['DHP'])/5 if 'DHP' in tree_data else size  # TODO : ajuster la formule pour la taille du point
        super().__init__(-size/2, -size/2, size, size)
        self.setBrush(Qt.green)
        self.setPos(x, y)
        self.setCursor(Qt.ArrowCursor)
        self.setFlags(QGraphicsItem.ItemIgnoresTransformations | QGraphicsItem.ItemIsSelectable)  # Ignore transformations to keep the point size constant

        self.tree_data = tree_data  # Store tree data, could be a dictionary or any structure
        self.parent = parent  # Référence au map_widget

        label = QGraphicsTextItem(tree_data['No_tige'], self)
        label.setFlag(QGraphicsTextItem.ItemIgnoresTransformations)
        label.adjustSize()
        label.setPos(0, -20)

    def mousePressEvent(self, event):
        # Modifie les données dans la fenêtre de propriétés
        if self.parent and hasattr(self.parent, 'new_tree_attributes'):
            self.parent.new_tree_attributes.emit(self.tree_data)
        
        super().mousePressEvent(event)

    def paint(self, painter, option, widget = ...):
        if self.isSelected():
            self.setBrush(Qt.yellow)
        else:
            self.setBrush(Qt.green)
        option.state &= ~QStyle.State_Selected
        return super().paint(painter, option, widget)

class Pointer(QGraphicsPolygonItem, QObject):
    '''
    Pointeur pour indiquer la position et la direction de la caméra dans la scène.
    '''
    def __init__(self):
        super().__init__(QPolygonF([QPointF(0, -10), QPointF(7, 10), QPointF(0, 4), QPointF(-7, 10), QPointF(0, -10)]))
        self.setBrush(Qt.red)
        self.setPos(0, 0)
        self.setTransformOriginPoint(0, 0)
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)  # Ignore transformations to keep the pointer size constant
        self.setZValue(1)

    def rotate_pointer(self, angle):
        self.setRotation(angle)
        self.setTransformOriginPoint(0, 0)

def readCSV(filename, delimiter=',', header = True):
    # lignes
    rows = []
    with open(filename, 'r', encoding="utf-8") as file:
        csvreader = csv.reader(file, delimiter=delimiter)
        if header:
            header = next(csvreader)
        for row in csvreader:
            rows.append(row)
    if header:
        return header, rows
    else:
        return rows

def CSV_to_dict(filename, delimiter=','):
    data = []

    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter=delimiter)
        for row in reader:
            data.append(dict(row))

    return data

def writeCSV(filename, data, header=None, delimiter=','):
    """
    Exporte des données vers un fichier CSV
    
    Args:
        filename (str): Nom du fichier CSV à créer
        data (list): Liste de listes contenant les données
        header (list, optional): Entête des colonnes
        delimiter (str): Séparateur (par défaut: virgule)
    """
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        csvwriter = csv.writer(file, delimiter=delimiter)
        
        # Écrire l'entête si fourni
        if header:
            csvwriter.writerow(header)
        
        # Écrire les données
        csvwriter.writerows(data)
    
    print(f"Données exportées vers {filename}")

def export_photo_info_to_csv(photo_info, filename):
    """
    Exporte les informations des photos vers un fichier CSV
    
    Args:
        photo_info (list): Liste des informations des photos
        filename (str): Nom (path complet) du fichier CSV de sortie
    """
    # Définir l'entête
    if isinstance(photo_info[0][0], list):
        header = ['image_avant', 'image_arrière', 'timestamp', 'x', 'y', 'z', 'roll', 'pitch', 'yaw']
    else:  # Si seules les images et timestamp sont disponibles
        header = ['image', 'timestamp', 'x', 'y', 'z', 'roll', 'pitch', 'yaw']

    # Préparer les données pour l'export
    csv_data = []
    for info in photo_info:
        if isinstance(info[0], list):
            row = [
                info[0][0], # image avant
                info[0][1], # image arrière
                info[1],    # timestamp
                info[2],    # x
                info[3],    # y
                info[4],    # z
                info[5],    # roll
                info[6],    # pitch
                info[7]     # yaw
            ]
        else:  # Si seules les images et timestamp sont disponibles
            row = [
                info[0],    # image
                info[1],    # timestamp
                info[2],    # x
                info[3],    # y
                info[4],    # z
                info[5],    # roll
                info[6],    # pitch
                info[7]     # yaw
            ]
        csv_data.append(row)
    
    # Exporter vers CSV
    writeCSV(filename, csv_data, header)

def readJSON(filename):
    with open(filename, 'r', encoding="utf-8") as file:
        data = json.load(file)
    return data

def writeJSON(filename, data):
    """
    Exporte des données vers un fichier JSON
    
    Args:
        filename (str): Nom du fichier JSON à créer
        data (dict): Dictionnaire contenant les données à exporter
    """
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)
    
    print(f"Données exportées vers {filename}")

def get_valid_pairs(directory):
    '''
    Parcourt les photos d'un répertoire et identifie les paires d'images lisibles
    
    Args : directory (str): Chemin du répertoire contenant les photos

    Retourne : liste [image avant,
                    image arrière,
                    timestamp image avant relatif à la première image du répertoire]
    '''
    photo_pairs = defaultdict(dict)
    first_photo_stamp = None

    # on parcourt les photos du répertoire pour construire un dictionnaire des paires
    for photo in os.listdir(directory):
        name, _ = os.path.splitext(photo)
        try:
            id, side, timestamp = name.split('_')
        except Exception:
            continue
        if first_photo_stamp == None: # TODO : rendre plus robuste. Assume que la première photo lue est la première photo prise (en théorie c,est toujours le cas)
            first_photo_stamp = int(timestamp)
        photo_pairs[id][side] = (photo, int(timestamp)-first_photo_stamp)

    valid_pairs = []

    # test de la lisibilité des paires
    for pair in photo_pairs.values():
        try:
            img1 = Image.open(os.path.join(directory, pair['F'][0]))
            img2 = Image.open(os.path.join(directory, pair['R'][0]))
            img1.verify()
            img2.verify()
        except Exception as e:
            # print('Invalid image:', photo[0]) TODO : trouver un message pertinent
            continue
        
        # on vérifie que la paire contient les deux côtés 'F' et 'R'
        if len(pair) == 2 and 'F' in pair and 'R' in pair:
            valid_pairs.append([[os.path.join(directory,pair['F'][0]), os.path.join(directory, pair['R'][0])], pair['F'][1]])
    
    print(f'{len(valid_pairs)} paires valides trouvées')

    return valid_pairs

def stitch_photos(pair_list, outdirectory, calibration=None, hugin_root = r'C:\Program Files\Hugin', index_start=0):
    '''
    Assemble des pairs de photos fisheye en photos panoramiques

    Args:
        pair_list (list): Liste de paires d'images à assembler
        outdirectory (str, optional): Répertoire de sortie pour les images assemblées. Si None, le répertoire d'entrée sera utilisé.
        calibration (dict, optional): Fichier de calibration
        hugin_root (str): Chemin vers le répertoire d'installation de Hugin

    Retourne : liste [image panoramique (path complet),
                    autres paramètres de pair_list]
    '''
    os.makedirs(os.path.join(outdirectory, 'panoramas'), exist_ok=True)  # Création du répertoire de sortie s'il n'existe pas

    # données de calibration
    if calibration is None:
        calibration_values = {'yF': 0, 'rF': -90, 'pF': 0, 'vF': 200, 
                            'aF': 0, 'bF': 0, 'cF': 0, 'dF': 0, 'eF': 0,
                            'yR': 180, 'rR': -90, 'pR': 0, 'vR': 200,
                            'aR': 0, 'bR': 0, 'cR': 0, 'dR': 0, 'eR': 0
                            }
        crop_values = {'lF': 50, 'rF': 1870, 'tF': 50, 'bF':1870,
                       'lR': 50, 'rR': 1870, 'tR': 50, 'bR':1870}
    else:
        forward_lens_params = calibration.get('lensParameters', {}).get('forwardLensCalibration', {})
        rearward_lens_params = calibration.get('lensParameters', {}).get('rearwardLensCalibration', {})
                        # lentille avant
        calibration_values = {'yF': forward_lens_params.get('yaw'), 'rF': forward_lens_params.get('roll'),
                       'pF': forward_lens_params.get('pitch'), 'vF': 200 if forward_lens_params.get('fov') == 0 else forward_lens_params.get('fov'),
                       'aF': forward_lens_params.get('coeffA'), 'bF': forward_lens_params.get('coeffB'), 'cF': forward_lens_params.get('coeffC'),
                       'dF': forward_lens_params.get('horizontalOffset'), 'eF': forward_lens_params.get('verticalOffset'),
                       # lentille arrière
                       'yR': rearward_lens_params.get('yaw'), 'rR': rearward_lens_params.get('roll'), 
                       'pR': rearward_lens_params.get('pitch'), 'vR': 200 if rearward_lens_params.get('fov') == 0 else rearward_lens_params.get('fov'),
                       'aR': rearward_lens_params.get('coeffA'), 'bR': rearward_lens_params.get('coeffB'), 'cR': rearward_lens_params.get('coeffC'),
                       'dR': rearward_lens_params.get('horizontalOffset'), 'eR': rearward_lens_params.get('verticalOffset')
                    }
        
        forward_lens_crop = calibration.get('lensParameters', {}).get('forwardLensSelectionArea', {})
        rearward_lens_crop = calibration.get('lensParameters', {}).get('rearwardLensSelectionArea', {})
                        # lentille avant
        crop_values = {'lF': forward_lens_crop.get('Left'), 'rF': forward_lens_crop.get('Right'),
                       'tF': forward_lens_crop.get('Top'), 'bF': forward_lens_crop.get('Bottom'),
                       # lentille arrière
                       'lR': rearward_lens_crop.get('Left'), 'rR': rearward_lens_crop.get('Right'),
                       'tR': rearward_lens_crop.get('Top'), 'bR': rearward_lens_crop.get('Bottom')}
        
        if all(value == 0 for value in crop_values.values()):
            # Si les valeurs de crop sont toutes à 0, on utilise des valeurs par défaut
            crop_values = {'lF': 50, 'rF': 1870, 'tF': 50, 'bF':1870,
                           'lR': 50, 'rR': 1870, 'tR': 50, 'bR':1870}

    # Procédure d'assemblage
    for i, pair in enumerate(pair_list):
        imgF_path = pair[0][0] # image avant
        imgR_path = pair[0][1] # image arrière

        # création de 2 projets Hugin
        subprocess.run([os.path.join(hugin_root, 'bin', 'pto_gen.exe'),
                '-o', 'projet1.pto',    # TODO : arranger le nom du projet
                '-p', '2',              # TODO : pourrait être lu dans le fichier de calibration
                '-c', f'{crop_values["lF"]},{crop_values["rF"]},{crop_values["tF"]},{crop_values["bF"]}',
                imgF_path])
        
        subprocess.run([os.path.join(hugin_root, 'bin', 'pto_gen.exe'),
                '-o', 'projet2.pto',    # TODO : arranger le nom du projet
                '-p', '2',              # TODO : pourrait être lu dans le fichier de calibration
                '-c', f'{crop_values["lR"]},{crop_values["rR"]},{crop_values["tR"]},{crop_values["bR"]}',
                imgR_path])

        # fusion des projets
        subprocess.run([os.path.join(hugin_root, 'bin', 'pto_merge.exe'),
                    '-o', 'projet_merge.pto',
                    'projet1.pto', 'projet2.pto'])

        # ajout d'une lentille pour l'image arrière
        subprocess.run([os.path.join(hugin_root, 'bin', 'pto_lensstack.exe'),
                        '-o', 'projet_merge.pto',
                        '--new-lens', 'i1',
                        'projet_merge.pto'])

        # ajout des paramètres de calibration
        subprocess.run([os.path.join(hugin_root, 'bin', 'pto_var.exe'),
                        '-o', 'projet_merge.pto',
                        # calibration avant
                        '--set', f'y0={calibration_values["yF"]}, r0={calibration_values["rF"]}, p0={calibration_values["pF"]}',
                        '--set', f'v0={calibration_values["vF"]}',
                        '--set', f'a0={calibration_values["aF"]}, b0={calibration_values["bF"]}, c0={calibration_values["cF"]}',
                        '--set', f'd0={calibration_values["dF"]}, e0={calibration_values["eF"]}',
                        # calibration arrière
                        '--set', f'y1={calibration_values["yR"]}, r1={calibration_values["rR"]}, p1={calibration_values["pR"]}',
                        '--set', f'v1={calibration_values["vR"]}',
                        '--set', f'a1={calibration_values["aR"]}, b1={calibration_values["bR"]}, c1={calibration_values["cR"]}',
                        '--set', f'd1={calibration_values["dR"]}, e1={calibration_values["eR"]}',
                        # paramètre à optimiser
                        '--opt', 'v0,v1,y1,p1,r1',
                        'projet_merge.pto'])
        
        # identification de points de contrôle
        subprocess.run([os.path.join(hugin_root, 'bin', 'cpfind.exe'),
                        '-o', 'projet_merge.pto',
                        '--fullscale',
                        'projet_merge.pto'])
        
        # optimisation des points de contrôle
        subprocess.run([os.path.join(hugin_root, 'bin', 'autooptimiser.exe'),
                        '-o', 'projet_merge.pto',
                        '-n',
                        'projet_merge.pto'])

        # assemblage des images
        subprocess.run([os.path.join(hugin_root, 'bin', 'nona.exe'),
                    '-o', os.path.join(outdirectory, 'panoramas', f'pano{i+index_start:04d}'), # nom de sortie avec numéro formaté     
                    '-m', 'JPEG',
                    'projet_merge.pto'])

        # on modifie le chemin de l'image pour correspondre à l'image panoramique créée
        pair_list[i][0] = f'pano{i+index_start:04d}.jpg'

    os.remove('projet1.pto')
    os.remove('projet2.pto')
    os.remove('projet_merge.pto')

    print('Les photos sont assemblées!')

    return pair_list

def get_photo_locations(photo_list, trajectory, trajectory_header, calibration): # TODO : utiliser la calibration???
    '''
    Associe les photos à leurs emplacements dans le trajet

    Args :
        photo_list (list): Liste des photos à associer
        trajectory (list): Liste des points de la trajectoire
        calibration (dict): Dictionnaire des paramètres de calibration

    Retourne : liste [info en entrée,
                    timestamp du trajet (écrase l'ancien timestamp de la photo)
                    x, y, z
                    roll, pitch, yaw (degrés)]
    '''
    first_traj_stamp = float(trajectory[0][0])
    iteration = 0

    for entry in trajectory:
        # on extrait le timestamp de l'entrée du trajet
        stamp = float(entry[trajectory_header.index('//world_time') if '//world_time' in trajectory_header else trajectory_header.index('%time')])
        # on vérifie si le timestamp est supérieur au ième timestamp des photos
        if stamp > (photo_list[iteration][1])/1000 + first_traj_stamp - 4:  # TODO : tweaker pour maximiser le fit (4 sec choisi par alignement visuel)
                                                                            # TODO : ajuster l'index pour que ça fonctionne
            roll, yaw, pitch = quaternion_to_euler(
                float(entry[trajectory_header.index('q0')]),
                float(entry[trajectory_header.index('q1')]),
                float(entry[trajectory_header.index('q2')]),
                float(entry[trajectory_header.index('q3')])
            )
            # on ajoute l'entrée du trajet à la liste des emplacements des photos et passe à la photo suivante
            photo_list[iteration][1] = stamp
            photo_list[iteration].extend([entry[trajectory_header.index('x')],
                                          entry[trajectory_header.index('y')],
                                          entry[trajectory_header.index('z')],
                                          roll, pitch, yaw
                                          ])
            iteration += 1
        if iteration >= len(photo_list):
            break

    print(f'Photos localisées!')

    return photo_list

def quaternion_to_euler(qw, qx, qy, qz):
    """
    Convertit un quaternion en angles d'Euler (roulis, tangage, lacet) en degrés.

    Args:
        qw, qx, qy, qz: Composantes du quaternion (w, x, y, z)

    Retourne:
        tuple: (roll, pitch, yaw) en degrés
    """
    # Normalize quaternion
    norm = math.sqrt(qw*qw + qx*qx + qy*qy + qz*qz)
    if norm == 0:
        return (0.0, 0.0, 0.0)
    
    qw, qx, qy, qz = qw/norm, qx/norm, qy/norm, qz/norm
    
    # Roll
    sinr_cosp = 2 * (qw * qx + qy * qz)
    cosr_cosp = 1 - 2 * (qx * qx + qy * qy)
    roll = math.atan2(sinr_cosp, cosr_cosp)
    
    # Pitch
    sinp = 2 * (qw * qy - qz * qx)
    if abs(sinp) >= 1:
        pitch = math.copysign(math.pi / 2, sinp)  # use 90 degrees if out of range
    else:
        pitch = math.asin(sinp)

    # Yaw
    siny_cosp = 2 * (qw * qz + qx * qy)
    cosy_cosp = 1 - 2 * (qy * qy + qz * qz)
    yaw = math.atan2(siny_cosp, cosy_cosp)
    
    # Convert from radians to degrees
    roll_deg = math.degrees(roll)
    pitch_deg = math.degrees(pitch)
    yaw_deg = math.degrees(yaw)
    
    # Return in the order: roll, pitch, yaw
    return (roll_deg, pitch_deg, yaw_deg)



#### Désuet ####
def export_gs_vision_to_csv(gs_vision, filename):
    """
    Exporte les données de vision GS vers un fichier CSV
    
    Args:
        gs_vision_data (list): Liste des données de vision GS
        filename (str): Nom du fichier CSV de sortie
    """
    header = ['image', 'timestamp', 'x', 'y', 'z', 'roll', 'pitch', 'yaw']
    gs_vision_data = gs_vision['images']
    # Préparer les données pour l'export
    csv_data = []
    for data in gs_vision_data:
        row = [
            data['imagePath'][2:],  # image
            data['time'],       # timestamp
            data['x'],          # x
            data['y'],          # y
            data['z'],          # z
            data['roll'],       # roll
            data['pitch'],      # pitch
            data['heading']     # yaw
        ]
        csv_data.append(row)
    
    # Exporter vers CSV
    writeCSV(filename, csv_data, header)

class VisualizerWindow(o3d.visualization.O3DVisualizer): # Ne gère pas le changement de site, crop de près
    def __init__(self, title, width, height, shared):
        super().__init__(title, width, height)

        self.shared = shared

        while not self.shared.cloud_updated:
            None

        las = lp.read(self.shared.cloud_path)

        total_pts = las.header.point_count
        decimation_factor = 10
        decimated_indices = np.arange(0, total_pts, decimation_factor)
        decimated_las = las.points[decimated_indices]
        print('Decimated')

        points = np.vstack((decimated_las.x, decimated_las.y, decimated_las.z)).transpose()
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        centered_pcd = pcd.translate(-pcd.get_center())
        print('Centered')

        material = o3d.visualization.rendering.MaterialRecord()
        material.shader = "depth"

        self.add_geometry("Point Cloud", centered_pcd, material=material)
        self.reset_camera_to_default()

    def on_frame(self):
        print("Running on_frame")
        if self.shared.cloud_updated:
        #     self.update_cloud(self.shared.cloud_path) # TODO
            print("Cloud updated")

        # if self.shared.updated:
        #     self.update_camera_position(self.shared.camera_position, self.shared.camera_direction)

    def update_cloud(self, cloud_path):
        las = lp.read(cloud_path)

        total_pts = las.header.point_count
        decimation_factor = 20
        decimated_indices = np.arange(0, total_pts, decimation_factor)
        decimated_las = las.points[decimated_indices]
        print('decimated')

        points = np.vstack((decimated_las.x, decimated_las.y, decimated_las.z)).transpose()
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        centered_pcd = pcd.translate(-pcd.get_center())
        print('centered')

        material = o3d.visualization.rendering.MaterialRecord()
        material.shader = "depth"

        try:
            self.remove_geometry('Point Cloud')
        except Exception as e:
            print(f"Error removing geometry: {e}")

        self.add_geometry("Point Cloud", centered_pcd, material=material)
        self.reset_camera_to_default()

    def update_camera_position(self, camera_position):
        None
        # self.setup_camera() # TODO

class YetAnotherViewer(): # Pas de crop de près et crop de loin, mais plante, gère pas le changement de site
    def __init__(self, shared):
        self.app = o3d.visualization.gui.Application.instance
        self.app.initialize()

        self.viewer = o3d.visualization.Visualizer()
        self.viewer.create_window(window_name="UdeS Forest View 3D", width=1024, height=768)

        self.view_control = self.viewer.get_view_control()
        self.view_control.set_up([0, 0, 1])
        self.view_control.set_front([0, 1, 0])
        self.view_control.set_constant_z_near(0.2)
        self.view_control.set_constant_z_far(15)

        self.shared = shared
        self.center = [0, 0, 0]
        self.material = o3d.visualization.rendering.MaterialRecord()
        self.material.shader = "depth"

        while not self.shared.cloud_updated:
            None

        self.update_cloud(self.shared.cloud_path)

    # def on_tick(self):
    #     print("Running on_tick")

    def update_cloud(self, cloud_path):
        las = lp.read(cloud_path)

        total_pts = las.header.point_count
        decimation_factor = 10
        decimated_indices = np.arange(0, total_pts, decimation_factor)
        decimated_las = las.points[decimated_indices]
        print('Decimated')

        points = np.vstack((decimated_las.x, decimated_las.y, decimated_las.z)).transpose()
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        self.center = pcd.get_center()
        centered_pcd = pcd.translate(-pcd.get_center())
        print('Centered')

        self.viewer.clear_geometries()

        self.viewer.add_geometry(centered_pcd)
        # self.scene.reset_camera_to_default()

        self.shared.cloud_updated = False  # Reset the flag after updating
