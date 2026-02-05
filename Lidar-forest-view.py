from Librairie import *
import pyvistaqt as pvqt
import laspy as lp

class AppManager(QObject):
    def __init__(self):
        super().__init__()

        # formulaire de données
        self.form = DataForm([['Répertoire de projet', 'project_dir', 'répertoire']])
        self.form.exec()

        # Chargement des données du projet
        # Photos
        try:
            self.photo_info = CSV_to_dict(os.path.join(self.form.paths['project_dir'], 'photo_info.csv'), ',')
        except FileNotFoundError:
            QMessageBox.critical(self, 'Avertissement', 'Le fichier photo_info.csv est introuvable dans le répertoire du projet. Les données de photos ne seont pas affichées')
            self.photo_info = None

        # Arbres
        try:
            self.tree_info = CSV_to_dict(os.path.join(self.form.paths['project_dir'], 'tree_info.csv'), ',')
        except FileNotFoundError:
            QMessageBox.warning(None, 'Avertissement', 'Le fichier tree_info.csv est introuvable dans le répertoire du projet. Les données d\'arbre ne seront pas affichées.')
            self.tree_info = None

        # Création des fenêtres
        self.photo_window = PhotoWindow(self.photo_info, self.tree_info, os.path.join(self.form.paths['project_dir'], 'panoramas')) # TODO voir si je retire les arguments d'initialisation
        self.lidar_window = LidarWindow()

        ##### Transfert potentiel #####
        # self.photo_window.map_widget.plot_photo_coordinates(self.photo_info)
        # if self.tree_info is not None :
        #     self.photo_window.map_widget.plot_tree_coordinates(self.tree_info)
        # self.photo_window.map_widget.create_pointer()

        # Connection des signaux
        self.photo_window.change_button.clicked.connect(self.change_site)
        self.photo_window.gl_widget.new_camera_direction.connect(self.lidar_window.update_camera_direction)
        self.photo_window.gl_widget.new_pointer_direction.connect(self.photo_window.map_widget.pointer.rotate_pointer)
        self.photo_window.map_widget.new_camera_position.connect(self.lidar_window.update_camera_position)
        self.photo_window.map_widget.new_panorama.connect(self.photo_window.gl_widget.load_image)
        self.photo_window.map_widget.new_tree_attributes.connect(self.photo_window.propriety_widget.load_data)
        self.lidar_window.lidar_tree_selected.connect(self.photo_window.map_widget.find_point)
        
        self.lidar_window.load_point_cloud(os.path.join(self.form.paths['project_dir'], 'cloud.laz'), 'main_cloud')
        if self.tree_info:
            self.lidar_window.add_trees(self.tree_info)
        self.lidar_window.load_point_cloud(os.path.join(self.form.paths['project_dir'], 'aero_cloud.laz'), 'aeroporté')

        ############# test pour les arbres géoréférencés
        # _, tree_coordinates = readCSV(r"path")
        # tree_coordinates = np.array(tree_coordinates)
        # tree_numbers = tree_coordinates[:,[0]]
        # tree_numbers.transpose()
        # tree_coordinates = tree_coordinates[:,[1,2,4]]
        # tree_coordinates = np.array(tree_coordinates, dtype = float)
        # tree_coordinates = tree_coordinates - self.lidar_window.translation
        # # print(tree_coordinates)
        # self.lidar_window.plotter.add_point_labels(tree_coordinates, tree_numbers, name='arbres', point_size = 30, point_color='pink', always_visible=True)
        #############

        self.photo_window.show()
        self.lidar_window.show()

    def change_site(self): #TODO changer la méthode
        '''Change le site en demandant à l'utilisateur de sélectionner un nouveau répertoire de projet'''

        # Ouvre le formulaire pour sélectionner un nouveau répertoire de projet
        self.form.exec()

        # Collecter les nouvelles informations
        try:
            self.photo_info = CSV_to_dict(os.path.join(self.form.paths['project_dir'], 'photo_info.csv'), ',')
        except FileNotFoundError:
            QMessageBox.critical(self, 'Avertissement', 'Le fichier photo_info.csv est introuvable dans le répertoire du projet. Les données de photos ne seont pas affichées')
            self.photo_info = None

        try:
            self.tree_info = CSV_to_dict(os.path.join(self.form.paths['project_dir'], 'tree_info.csv'), ',')
        except FileNotFoundError:
            QMessageBox.warning(self, 'Avertissement', 'Le fichier tree_info.csv est introuvable dans le répertoire du projet. Les données d\'arbre ne seront pas affichées.')
            self.tree_info = None

        self.photo_window.change_site(self.photo_info, self.tree_info, os.path.join(self.form.paths['project_dir'], 'panoramas'))
        self.lidar_window.change_site(os.path.join(self.form.paths['project_dir'], 'cloud.laz'), self.tree_info)

        print('Nouveau site chargé')

class PhotoWindow(QMainWindow):
    def __init__(self, photo_info, tree_info, photo_dir):
        super().__init__()

        # self.photo_dir = photo_dir

        self.setWindowTitle("UdeS Forest View") # TODO : changer le nom de la fenêtre
        self.setGeometry(300, 300, 800, 600)

        # Création des widgets principaux
        self.gl_widget = GLWidget(self, photo_dir)
        self.map_widget = CustomMapWidget(photo_info, tree_info)
        if tree_info is None :
            self.propriety_widget = ProprietyWidget([])
        else:
            self.propriety_widget = ProprietyWidget(list(k for k in tree_info[0].keys() if k not in {'x', 'y', 'z'}))
        self.change_button = QPushButton('Changer de site')

        # Création de la disposition principale
        propriety_box = QGroupBox('Propriétés')
        propriety_box_layout = QVBoxLayout()
        propriety_box_layout.setContentsMargins(1, 0, 1, 1)
        propriety_box_layout.setSpacing(0)
        propriety_box_layout.addWidget(self.propriety_widget)
        propriety_box.setLayout(propriety_box_layout)
        
        right_layout = QVBoxLayout()
        right_layout.addWidget(propriety_box, 2)
        right_layout.addWidget(self.map_widget, 3)
        right_layout.addWidget(self.change_button)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.gl_widget , 3)
        main_layout.addLayout(right_layout, 1)
                
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def change_site(self, photo_info, tree_info, photo_dir): #TODO changer la méthode
        '''Change le site en demandant à l'utilisateur de sélectionner un nouveau répertoire de projet'''

        # Réinitialise la carte
        self.gl_widget.new_pointer_direction.disconnect()
        self.map_widget.reset()
        self.gl_widget.new_pointer_direction.connect(self.map_widget.pointer.rotate_pointer)

        self.map_widget.plot_photo_coordinates(photo_info)
        self.map_widget.plot_tree_coordinates(tree_info)
        self.map_widget.pointer.setPos(float(photo_info[0]['x']), -float(photo_info[0]['y']))

        self.map_widget.fitInView(self.map_widget.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
        self.map_widget.scene.setSceneRect(self.map_widget.scene.itemsBoundingRect().marginsAdded(QMarginsF(10,10,10,10)))

        # Réinitialise les propriétés
        self.propriety_widget.reset()
        self.propriety_widget.set_fields(list(k for k in tree_info[0].keys() if k not in {'x', 'y', 'z'}))

        # Réinitialise la vue photo
        self.gl_widget.reset()
        self.gl_widget.photo_dir = photo_dir

    ## désuet ## pourrait servir à tout fermer d'un coup via un signal
    # def closeEvent(self, event):
    #     '''Gère la fermeture de la fenêtre'''
    #     with self.shared.lock:
    #         self.shared.running = False
    #     event.accept()

class LidarWindow(QMainWindow):
    camera_parameters = [[0, 0, 0], # paramètres de la vue
                         [1, 0, 0],
                         [0, 0, 1]]
    translation = None # Translation appliquée au nuage de points
    lidar_tree_selected = pyqtSignal(object)

    def __init__(self):
        super().__init__()

        self.setWindowTitle('UdeS Forest View 3D') # TODO changer le nom de la fenêtre quand un nom sera choisi
        self.setGeometry(100, 100, 800, 600)

        self.plotter = pvqt.QtInteractor(self)
        self.setCentralWidget(self.plotter.interactor)

        self.plotter.set_viewup([0, 0, 1])
        self.plotter.camera.view_angle = 90
        self.view_depth = 15

        self.plotter.enable_point_picking(callback=self.point_picked, color='yellow', point_size=30)
        self.plotter.enable_eye_dome_lighting()

    def load_point_cloud(self, point_cloud_path, actor_name):
        try:
            las = lp.read(point_cloud_path)
            pcd = np.vstack((las.x, las.y, las.z)).transpose()

            if self.translation is None:
                self.translation = np.mean(pcd, axis=0)

            centered_pcd = pcd - self.translation

            self.plotter.add_mesh(centered_pcd, name=actor_name ,style='points', point_size=2, label=actor_name, pickable=False)
        except FileNotFoundError:
            print(f'Le fichier {point_cloud_path} n\' , pas été trouvé')


    def add_trees(self, tree_data):
        tree_pcd = np.vstack(([entry['x'] for entry in tree_data],
                              [entry['y'] for entry in tree_data],
                              [entry['z'] for entry in tree_data])).transpose()
        tree_pcd = np.array(tree_pcd, dtype = float)

        if self.translation is None:
            self.translation = np.mean(tree_pcd, axis=0)

        tree_pcd = tree_pcd - self.translation

        labels = [entry['No_tige'] for entry in tree_data]

        self.plotter.add_point_labels(tree_pcd, labels, name='arbres', point_size=30, point_color='pink', always_visible=True, pickable=True)

    def update_camera_position(self, camera_position):
        centered_position = camera_position - self.translation
        self.camera_parameters[1] -= self.camera_parameters[0] - centered_position
        self.camera_parameters[0] = centered_position
        self.plotter.camera_position = self.camera_parameters
        self.plotter.camera.clipping_range = (0.5, self.view_depth)

    def update_camera_direction(self, camera_direction):
        if camera_direction[2] == 1:
            self.camera_parameters[2] = [0, 1, 0]
        else:
            self.camera_parameters[2] = [0, 0, 1]

        self.camera_parameters[1] = self.camera_parameters[0] + camera_direction
        self.plotter.camera_position = self.camera_parameters
        self.plotter.camera.clipping_range = (0.5, self.view_depth/(1.1-abs(camera_direction[2])**3))

    def point_picked(self, picked_point):
        picked_point = picked_point + self.translation
        self.lidar_tree_selected.emit(picked_point)

    def change_site(self, cloud_path, tree_info):
        self.reset()
        self.load_point_cloud(cloud_path, 'main_cloud')
        self.add_trees(tree_info)

    def reset(self):
        self.plotter.clear_actors()
        self.camera_parameters = [[0, 0, 0],
                                  [1, 0, 0],
                                  [0, 0, 1]]
        self.plotter.camera_position = self.camera_parameters
        self.translation = None

    def closeEvent(self, event):
        self.plotter.close()
        super().closeEvent(event)

if __name__ == '__main__':

    fmt = QSurfaceFormat()
    fmt.setVersion(4, 5)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    QSurfaceFormat.setDefaultFormat(fmt)

    app = QApplication([])
    manager = AppManager()
    app.exec()
