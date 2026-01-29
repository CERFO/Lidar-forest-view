from Librairie import *
import shutil

class ProjectMaker(QWidget):
    def __init__(self):
        super().__init__()
        
        choice = QMessageBox(self)
        choice.setWindowTitle("Choix de l'action")
        choice.setText("Voulez-vous créer un nouveau projet ou ajouter des photos à un projet existant?")
        create = choice.addButton("Créer un nouveau projet", QMessageBox.ActionRole)
        add = choice.addButton("Ajouter des photos à un projet existant", QMessageBox.ActionRole)
        choice.exec_()

        if choice.clickedButton() == create:
            self.create_project()
        elif choice.clickedButton() == add:
            self.add_scans()

    def create_project(self):
        # Saisie de l'emplacement du projet
        base_form = DataForm([['Répertoire de sortie', 'project_out_dir', 'répertoire']])
        base_form.exec()

        # Saisie du nom du projet
        project_name, accepted = QInputDialog.getText(self, 'Nom du projet', 'Entrez le nom du projet :')

        while True:
            if accepted and project_name == '':
                QMessageBox.warning(self, 'Erreur', 'Le nom du projet ne peut pas être vide.')
                project_name, _ = QInputDialog.getText(self, 'Nom du projet', 'Entrez le nom du projet :')
            elif not accepted:
                # Show a message box to inform the user
                reply = QMessageBox.question(self, 'Vous partez déjà?',
                                            'Êtes-vous sûr de vouloir quitter?',
                                            QMessageBox.Yes | QMessageBox.No,
                                            QMessageBox.No)
                    
                if reply == QMessageBox.Yes:
                    sys.exit()
                else:
                    project_name, _ = QInputDialog.getText(self, 'Nom du projet', 'Entrez le nom du projet :')
            else:
                break
        
        # Création du répertoire du projet
        project_path = os.path.join(base_form.paths['project_out_dir'], project_name)

        while True:
            try:
                os.makedirs(project_path)
                break
            except FileExistsError:
                # Indiquer à l'utilisateur que le dossier existe déjà
                reply = QMessageBox.question(self, 'Dossier existant', 
                                            'Ce fichier existe déjà. Voulez vous écrire par dessus?',
                                            QMessageBox.Yes | QMessageBox.No,
                                            QMessageBox.No)
                
                if reply == QMessageBox.No:
                    project_name, _ = QInputDialog.getText(self, 'Nom du projet', 'Entrez le nom du projet :')
                    project_path = os.path.join(base_form.paths['project_out_dir'], project_name)
                
                # Si l'utilisateur accepte, on supprime les fichiers existants
                elif reply == QMessageBox.Yes:
                    if os.path.exists(os.path.join(base_form.paths['project_out_dir'], project_name, 'photo_info.csv')):
                        os.remove(os.path.join(base_form.paths['project_out_dir'], project_name, 'photo_info.csv'))
                    if os.path.exists(os.path.join(base_form.paths['project_out_dir'], project_name, 'tree_info.csv')):
                        os.remove(os.path.join(base_form.paths['project_out_dir'], project_name, 'tree_info.csv'))
                    if os.path.exists(os.path.join(base_form.paths['project_out_dir'], project_name, 'panoramas')):
                        shutil.rmtree(os.path.join(base_form.paths['project_out_dir'], project_name, 'panoramas'), ignore_errors=True)
                    break
        
        # Création des sous-répertoires nécessaires
        os.makedirs(os.path.join(project_path, 'panoramas'), exist_ok=True)

        # Saisie du nombre des scans à incorporer
        num_scans, _ = QInputDialog.getInt(self, 'Nombre de scans', 'Entrez le nombre de scans à incorporer :', 1, 1, 100)
        total_data = []
        scans_info = []

        # Pour chaque scan, on demande les informations nécessaires, puis on traite les photos 
        for i in range(num_scans):
            scan_form = ScanForm(i+1)
            scan_form.exec()

            scans_info.append(scan_form.get_info())
        
        index = 0
        for info in scans_info:
            if info[0] == 'GS-vision':
                new_data, index = self.add_gs_vision_scan(info[1], info[2], index, project_path)
            elif info[0] == 'Insta 360':
                new_data, index = self.add_insta_360_scan(info[1], info[2], index, project_path)
            elif info[0] == 'Eagle':
                new_data, index = self.add_eagle_scan(info[1], info[2], index, project_path)
            elif info[0] == 'Hémisphérique':
                new_data, index = self.add_plain_scan(info[1], info[2], info[3], index, project_path, info[4])

            total_data.extend(new_data)

        self.export_data(total_data, project_path)

    def add_scans(self):
        # Saisie de l'emplacement du projet
        base_form = DataForm([['Répertoire du projet', 'project_in_dir', 'répertoire']])
        base_form.exec()

        project_path = base_form.paths['project_in_dir']

        # Saisie du nombre des scans à incorporer
        num_scans, _ = QInputDialog.getInt(self, 'Nombre de scans', 'Entrez le nombre de scans à incorporer :', 1, 1, 100)
        _, total_data = readCSV(os.path.join(base_form.paths['project_in_dir'], 'photo_info.csv'))
        scans_info = []

        for i in range(num_scans):
            scan_form = ScanForm(i+1)
            scan_form.exec()

            scans_info.append(scan_form.get_info())

        index = len(total_data)
        for info in scans_info:
            if info[0] == 'GS-vision':
                new_data, index = self.add_gs_vision_scan()
            elif info[0] == 'Insta 360':
                new_data, index = self.add_insta_360_scan(info[1], info[2], index, project_path)
            elif info[0] == 'Eagle':
                new_data, index = self.add_eagle_scan()
            elif info[0] == 'Hémisphérique':
                new_data, index = self.add_plain_scan()

            total_data.extend(new_data)

        self.export_data(total_data, base_form.paths['project_in_dir'])

    def add_insta_360_scan(self, traj_photos_path, photo_dir, index, project_path):
        traj_photos = CSV_to_dict(traj_photos_path)
        out_data = []

        for data in traj_photos:
            entry_name = f'pano{index:04d}.jpg'
            roll = float(data['roll'])
            pitch = float(data['pitch'])
            yaw = float(data['yaw'])
            yaw_corrected_deg = math.degrees(math.atan2(
                math.sin(yaw) * math.cos(pitch) + math.cos(yaw) * math.sin(roll) * math.sin(pitch),
                math.cos(yaw) * math.cos(pitch) - math.sin(yaw) * math.sin(roll) * math.sin(pitch))) + 90
            entry = [
                entry_name,         # image
                data['X..world_time'],  # timestamp
                data['x'],          # x
                data['y'],          # y
                data['z'],          # z
                0,                  # roll
                0,                  # pitch
                yaw_corrected_deg   # yaw
                ]
            out_data.append(entry)

            src_path = os.path.join(photo_dir, data['name'])
            dst_path = os.path.join(project_path, 'panoramas', entry_name)
            index += 1
            shutil.copy2(src_path, dst_path)

        return out_data, index

    def add_gs_vision_scan(self, gs_vision, photo_dir, index,  project_path):
        gs_vision = readJSON(gs_vision)
        gs_vision_data = gs_vision['images']
        out_data = []

        for data in gs_vision_data:
            entry_name = f'pano{index:04d}.jpg'
            entry = [
                entry_name,         # image
                data['time'],       # timestamp
                data['x'],          # x
                data['y'],          # y
                data['z'],          # z
                data['roll'],       # roll
                data['pitch'],      # pitch
                data['heading']     # yaw
                ]
            out_data.append(entry)

            src_path = os.path.join(photo_dir, data['imagePath'][2:])
            dst_path = os.path.join(project_path, 'panoramas', entry_name)
            index += 1
            shutil.copy2(src_path, dst_path)

        return out_data, index

    def add_eagle_scan(self, traj, photo_dir, index, project_path):
        raise NotImplementedError

    def add_plain_scan(self, traj_path, cam_cal_path, photo_dir, index, project_path, hugin_root):
        out_data = []

        traj_head, traj = readCSV(traj_path, ' ')
        calibration = readJSON(cam_cal_path)

        photo_info = get_valid_pairs(photo_dir)
        photo_info = get_photo_locations(photo_info, traj, traj_head, calibration)

        out_data.extend(photo_info)

        stitch_photos(out_data, project_path, calibration, hugin_root, index_start=index)

        index += len(out_data)

        return out_data, index

    def export_data(self, photo_info, project_path):
        export_photo_info_to_csv(photo_info, os.path.join(project_path, 'photo_info.csv'))

        print("Exportations CSV terminées!")

class ScanForm(QDialog):
    def __init__(self, no_scan):
        super().__init__()
        self.setWindowTitle(f'Scan {no_scan} - Informations')

        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.Dialog)

        self.memory = readJSON('memory.json') if os.path.exists('memory.json') else {}

        self.layout = QFormLayout()

        self.combo_box = QComboBox()
        self.combo_box.insertItems(0, ['GS-vision', 'Insta 360', 'Eagle', 'Hémisphérique'])
        self.layout.addRow('Type de données', self.combo_box)

        self.trajectory = BrowseLayout('Trajectoire photos', 'traj_photos_path', 'file', self.memory)
        self.layout.addRow('Trajectoire photos', self.trajectory)
        self.gs_vision = BrowseLayout('GS-Vision', 'gs_vision_path', 'file', self.memory)
        self.layout.addRow('GS-Vision', self.gs_vision)
        self.calibration = BrowseLayout('Calibration', 'cam_cal_path', 'file', self.memory)
        self.layout.addRow('Calibration', self.calibration)
        self.pano_photos = BrowseLayout('Photos panoramiques', 'panoramic_photos_dir', 'répertoire', self.memory)
        self.layout.addRow('Photos panoramiques', self.pano_photos)
        self.fisheye_photos = BrowseLayout('Photos fisheye', 'fisheye_photos_dir', 'répertoire', self.memory)
        self.layout.addRow('Photos fisheye', self.fisheye_photos)
        self.hugin = BrowseLayout('Racine Hugin', 'hugin_root', 'répertoire', self.memory)
        self.layout.addRow('Racine Hugin', self.hugin)

        self.submit_button = QPushButton('Soumettre')
        self.submit_button.clicked.connect(self.submit_data)
        self.layout.addRow(self.submit_button)

        self.setLayout(self.layout)

    def submit_data(self): # TODO ajouter une sécurité contre les formulaires incomplets
        for row in range(self.layout.rowCount()):
            item = self.layout.itemAt(row, QFormLayout.ItemRole.FieldRole)
            if isinstance(item, BrowseLayout) and item.line_edit.text() != '':
                if item.field in self.memory:
                    self.memory[item.field] = item.line_edit.text()
                else:
                    self.memory.update({item.field: item.line_edit.text()})
        
        self.close()

    def get_info(self):
        if self.combo_box.currentText() == 'GS-vision':
            return [self.combo_box.currentText(),
                    self.gs_vision.line_edit.text(),
                    self.pano_photos.line_edit.text()]

        elif self.combo_box.currentText() == 'Insta 360':
            return [self.combo_box.currentText(),
                    self.trajectory.line_edit.text(),
                    self.pano_photos.line_edit.text()]

        elif self.combo_box.currentText() == 'Eagle':
            return [self.combo_box.currentText(),
                    self.trajectory.line_edit.text(),
                    self.fisheye_photos.line_edit.text()]

        elif self.combo_box.currentText() == 'Hémisphérique':
            return [self.combo_box.currentText(),
                    self.trajectory.line_edit.text(),
                    self.calibration.line_edit.text(),
                    self.fisheye_photos.line_edit.text(),
                    self.hugin.line_edit.text()]

class BrowseLayout(QHBoxLayout):
    def __init__(self, label_text, field_name, path_type, memory):
        super().__init__()
        self.field = field_name
        self.line_edit = QLineEdit(text = memory[field_name] if field_name in memory else '')
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(lambda _, le=self.line_edit: self.browse_file(le, label_text, path_type))

        self.addWidget(self.line_edit)
        self.addWidget(browse_button)

    def browse_file(self, line_edit, caption, path_type):
        '''Ouvre une boîte de dialogue pour sélectionner un fichier ou un répertoire'''
        if path_type == 'file':
            file_path, _ = QFileDialog.getOpenFileName(None, f'Sélectionnez {caption}') # TODO : ajouter un filtre pour les fichiers (requiert un argument supplémentaire)
        elif path_type == 'répertoire':
            file_path = QFileDialog.getExistingDirectory(None, f'Sélectionnz {caption}')

        if file_path:
            line_edit.setText(file_path)

if __name__ == '__main__':
    app = QApplication([])
    window = ProjectMaker()
