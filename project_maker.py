from Librairie import *
import shutil

from forest_view.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

class ProjectMaker(QWidget):
    def __init__(self):
        super().__init__()

        choice = QMessageBox(self)
        choice.setWindowTitle("Choix de l'action")
        choice.setText("Voulez-vous créer un nouveau projet ou ajouter des photos à un projet existant?")
        create = choice.addButton("Créer un nouveau projet", QMessageBox.ButtonRole.ActionRole)
        add = choice.addButton("Ajouter des photos à un projet existant", QMessageBox.ButtonRole.ActionRole)
        choice.exec()

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
                new_data, index = self.add_insta_360_scan(info[1], info[2], info[3], index, project_path)
            elif info[0] == 'Eagle':
                new_data, index = self.add_eagle_scan(info[1], info[2], index, project_path)
            elif info[0] == 'Hémisphérique':
                new_data, index = self.add_plain_scan(info[1], info[2], info[3], index, project_path, info[4])

            total_data.extend(new_data)

        self.export_data(total_data, project_path)

    def add_scans(self):
        # Saisie de l'emplacement du projet (avec validation pour projets incomplets)
        while True:
            base_form = DataForm([['Répertoire du projet', 'project_in_dir', 'répertoire']])
            base_form.exec()

            if not base_form.paths.get('project_in_dir'):
                return  # utilisateur a annulé (fermeture sans soumettre)

            project_path = base_form.paths['project_in_dir']

            if not os.path.isdir(project_path):
                reply = QMessageBox.question(
                    self, 'Répertoire invalide',
                    f"Le répertoire n'existe pas ou n'est pas accessible :\n{project_path}\n\nChoisir un autre répertoire ou quitter ?",
                    QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Ok
                )
                if reply == QMessageBox.StandardButton.Cancel:
                    return
                continue

            photo_info_path = os.path.join(project_path, 'photo_info.csv')
            if not os.path.isfile(photo_info_path):
                choice = QMessageBox(self)
                choice.setWindowTitle('Projet incomplet')
                choice.setIcon(QMessageBox.Icon.Warning)
                choice.setText(
                    "Ce répertoire ne contient pas photo_info.csv.\n\n"
                    "Un projet existant doit déjà avoir au moins un scan exporté (fichier créé après le premier scan). "
                    "Si le projet est en cours de création ou vide, créez d'abord un nouveau projet."
                )
                btn_other = choice.addButton('Choisir un autre répertoire', QMessageBox.ButtonRole.ActionRole)
                btn_new = choice.addButton('Créer un nouveau projet', QMessageBox.ButtonRole.ActionRole)
                btn_quit = choice.addButton('Quitter', QMessageBox.ButtonRole.RejectRole)
                choice.exec()
                if choice.clickedButton() == btn_new:
                    self.create_project()
                    return
                if choice.clickedButton() == btn_quit:
                    QApplication.quit()
                    return
                continue
            break

        # Saisie du nombre des scans à incorporer
        num_scans, _ = QInputDialog.getInt(self, 'Nombre de scans', 'Entrez le nombre de scans à incorporer :', 1, 1, 100)
        _, total_data = readCSV(os.path.join(project_path, 'photo_info.csv'))
        scans_info = []

        for i in range(num_scans):
            scan_form = ScanForm(i+1)
            scan_form.exec()

            scans_info.append(scan_form.get_info())

        index = len(total_data)
        for info in scans_info:
            if info[0] == 'GS-vision':
                new_data, index = self.add_gs_vision_scan(info[1], info[2], index, project_path)
            elif info[0] == 'Insta 360':
                new_data, index = self.add_insta_360_scan(info[1], info[2], info[3], index, project_path)
            elif info[0] == 'Eagle':
                new_data, index = self.add_eagle_scan(info[1], info[2], index, project_path)
            elif info[0] == 'Hémisphérique':
                new_data, index = self.add_plain_scan(info[1], info[2], info[3], index, project_path, info[4])

            total_data.extend(new_data)

        self.export_data(total_data, project_path)

    def add_insta_360_scan(self, traj_photos_path, photo_dir, camera_orientation,  index, project_path):
        traj_photos = CSV_to_dict(traj_photos_path)
        out_data = []

        for data in traj_photos:
            entry_name = f'pano{index:04d}.jpg'
            roll = float(data['roll'])
            pitch = float(data['pitch'])
            yaw = float(data['yaw'])
            if camera_orientation == 'Gauche':
                yaw_offset = -90
            elif camera_orientation == 'Droite':
                yaw_offset = 90
            elif camera_orientation == 'Avant':
                yaw_offset = 180
            else:
                yaw_offset = 0
            yaw_corrected_deg = math.degrees(math.atan2(
                math.sin(yaw) * math.cos(pitch) + math.cos(yaw) * math.sin(roll) * math.sin(pitch),
                math.cos(yaw) * math.cos(pitch) - math.sin(yaw) * math.sin(roll) * math.sin(pitch))
            ) + yaw_offset
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
                entry_name,                     # image
                data['time'],                   # timestamp
                data['x'],                      # x
                data['y'],                      # y
                data['z'],                      # z
                data['roll'],                   # roll
                data['pitch'],                  # pitch
                float(data['heading']) + 180    # yaw
            ]
            out_data.append(entry)

            src_path = os.path.join(photo_dir, data['imagePath'][2:])
            dst_path = os.path.join(project_path, 'panoramas', entry_name)
            index += 1
            shutil.copy2(src_path, dst_path)

        return out_data, index

    def add_eagle_scan(self, traj, photo_dir, index, project_path):
        # insérer 180 de offset au yaw lors de l'impléentation
        raise NotImplemented

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
        logger.info("Exportations CSV terminées!")


def _load_scan_field_help():
    """Charger les champs d'aide à partir du fichier forest_view/field_hints.json."""
    try:
        import forest_view.forms as _fv_forms
        _path = os.path.join(os.path.dirname(_fv_forms.__file__), 'field_hints.json')
        _data = readJSON(_path) if os.path.exists(_path) else {}
        return _data.get('scan_field_help', {})
    except Exception:
        return {}

SCAN_FIELD_HELP = _load_scan_field_help()


def _make_label_with_help(label_text, help_by_type):
    """Crée un widget label + icône ⓘ. help_by_type est un dict { type_scan: tooltip }; la forme met à jour le tooltip dans on_text_change."""
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    lbl = QLabel(label_text)
    layout.addWidget(lbl)
    info = QLabel("ⓘ")
    info.setCursor(Qt.CursorShape.WhatsThisCursor)
    font = info.font()
    font.setPointSize(max(8, font.pointSize() - 1))
    info.setFont(font)
    info.setStyleSheet("")  # use theme text color (white on dark, black on light)
    layout.addWidget(info)
    layout.addStretch()
    return widget, info, help_by_type


class ScanForm(QDialog):
    def __init__(self, no_scan):
        super().__init__()
        self.setWindowTitle(f'Scan {no_scan} - Informations')

        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)

        self.memory = readJSON('appsettings.json') if os.path.exists('appsettings.json') else {}

        self.layout = QFormLayout()
        self._help_info_labels = []  # liste de (info_label, help_by_type)

        self.combo_box = QComboBox()
        self.combo_box.insertItems(0, ['Sélectionner', 'GS-vision', 'Insta 360', 'Eagle', 'Hémisphérique'])
        self.combo_box.currentTextChanged.connect(self.on_text_change)
        self.layout.addRow('Type de données', self.combo_box)

        traj_label, traj_info, traj_help = _make_label_with_help('Trajectoire photos', {
            t: SCAN_FIELD_HELP[t]['trajectory'] for t in ('Insta 360', 'Eagle', 'Hémisphérique')
            if t in SCAN_FIELD_HELP and 'trajectory' in SCAN_FIELD_HELP[t]
        })
        self._help_info_labels.append((traj_info, traj_help))
        self.trajectory = BrowseLayout('Trajectoire photos', 'traj_photos_path', 'file', self.memory)
        self.layout.addRow(traj_label, self.trajectory)
        self.layout.setRowVisible(self.trajectory, False)

        gs_label, gs_info, gs_help = _make_label_with_help('GS-Vision', {'GS-vision': SCAN_FIELD_HELP['GS-vision']['gs_vision']})
        self._help_info_labels.append((gs_info, gs_help))
        self.gs_vision = BrowseLayout('GS-Vision', 'gs_vision_path', 'file', self.memory)
        self.layout.addRow(gs_label, self.gs_vision)
        self.layout.setRowVisible(self.gs_vision, False)

        cal_label, cal_info, cal_help = _make_label_with_help('Calibration', {'Hémisphérique': SCAN_FIELD_HELP['Hémisphérique']['calibration']})
        self._help_info_labels.append((cal_info, cal_help))
        self.calibration = BrowseLayout('Calibration', 'cam_cal_path', 'file', self.memory)
        self.layout.addRow(cal_label, self.calibration)
        self.layout.setRowVisible(self.calibration, False)

        pano_label, pano_info, pano_help = _make_label_with_help('Photos panoramiques', {
            t: SCAN_FIELD_HELP[t]['pano_photos'] for t in ('Insta 360', 'GS-vision')
        })
        self._help_info_labels.append((pano_info, pano_help))
        self.pano_photos = BrowseLayout('Photos panoramiques', 'panoramic_photos_dir', 'répertoire', self.memory)
        self.layout.addRow(pano_label, self.pano_photos)
        self.layout.setRowVisible(self.pano_photos, False)

        fisheye_label, fisheye_info, fisheye_help = _make_label_with_help('Photos fisheye', {
            t: SCAN_FIELD_HELP[t]['fisheye_photos'] for t in ('Eagle', 'Hémisphérique')
        })
        self._help_info_labels.append((fisheye_info, fisheye_help))
        self.fisheye_photos = BrowseLayout('Photos fisheye', 'fisheye_photos_dir', 'répertoire', self.memory)
        self.layout.addRow(fisheye_label, self.fisheye_photos)
        self.layout.setRowVisible(self.fisheye_photos, False)

        hugin_label, hugin_info, hugin_help = _make_label_with_help('Racine Hugin', {'Hémisphérique': SCAN_FIELD_HELP['Hémisphérique']['hugin']})
        self._help_info_labels.append((hugin_info, hugin_help))
        self.hugin = BrowseLayout('Racine Hugin', 'hugin_root', 'répertoire', self.memory)
        self.layout.addRow(hugin_label, self.hugin)
        self.layout.setRowVisible(self.hugin, False)

        cam_label, cam_info, cam_help = _make_label_with_help('Orientation de la caméra', {'Insta 360': SCAN_FIELD_HELP['Insta 360']['camera_orientation']})
        self._help_info_labels.append((cam_info, cam_help))
        self.camera_orientation = QComboBox()
        self.camera_orientation.insertItems(0, ['Gauche', 'Droite', 'Avant', 'Arrière'])
        self.layout.addRow(cam_label, self.camera_orientation)
        self.layout.setRowVisible(self.camera_orientation, False)

        for info, _ in self._help_info_labels:
            info.installEventFilter(self)

        self.submit_button = QPushButton('Soumettre')
        self.submit_button.clicked.connect(self.submit_data)
        self.layout.addRow(self.submit_button)

        self.setLayout(self.layout)
        self.adjustSize()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Enter:
            for info, help_by_type in self._help_info_labels:
                if obj is info and help_by_type:
                    text = help_by_type.get(self.combo_box.currentText(), "")
                    if text:
                        QToolTip.showText(QCursor.pos(), text)
                    break
        elif event.type() == QEvent.Type.Leave:
            for info, _ in self._help_info_labels:
                if obj is info:
                    QToolTip.hideText()
                    break
        return super().eventFilter(obj, event)

    def on_text_change(self, new_text):
        self.layout.setRowVisible(self.trajectory, new_text == 'Insta 360' or new_text == 'Eagle' or new_text == 'Hémisphérique')
        self.layout.setRowVisible(self.gs_vision, new_text == 'GS-vision')
        self.layout.setRowVisible(self.calibration, new_text == 'Hémisphérique')
        self.layout.setRowVisible(self.pano_photos, new_text == 'GS-vision' or new_text == 'Insta 360')
        self.layout.setRowVisible(self.fisheye_photos, new_text == 'Eagle' or new_text == 'Hémisphérique')
        self.layout.setRowVisible(self.hugin, new_text == 'Hémisphérique')
        self.layout.setRowVisible(self.camera_orientation, new_text == 'Insta 360')
        for info, help_by_type in self._help_info_labels:
            info.setToolTip(help_by_type.get(new_text, "") if help_by_type else "")
        self.adjustSize()

    def submit_data(self): # TODO ajouter une sécurité contre les formulaires incomplets
        for row in range(self.layout.rowCount()):
            item = self.layout.itemAt(row, QFormLayout.ItemRole.FieldRole)
            if isinstance(item, BrowseLayout) and item.line_edit.text() != '':
                if item.field in self.memory:
                    self.memory[item.field] = item.line_edit.text()
                else:
                    self.memory.update({item.field: item.line_edit.text()})
        writeJSON('appsettings.json', self.memory)
        self.close()

    def get_info(self):
        if self.combo_box.currentText() == 'GS-vision':
            return [self.combo_box.currentText(),
                    self.gs_vision.line_edit.text(),
                    self.pano_photos.line_edit.text()]

        elif self.combo_box.currentText() == 'Insta 360':
            return [self.combo_box.currentText(),
                    self.trajectory.line_edit.text(),
                    self.pano_photos.line_edit.text(),
                    self.camera_orientation.currentText()]

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
