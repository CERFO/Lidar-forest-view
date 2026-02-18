from Librairie import *
import shutil

from forest_view.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        action = QMessageBox(self)
        action.setWindowTitle("Choix de l'action")
        action.setText("Voulez-vous créer un nouveau projet ou ajouter des photos à un projet existant?")
        create = action.addButton("Créer un nouveau projet", QMessageBox.ActionRole)
        add = action.addButton("Ajouter des photos à un projet existant", QMessageBox.ActionRole)
        action.exec_()

        if action.clickedButton() == create:
            self.create_project()
        elif action.clickedButton() == add:
            self.add_scans()

    def create_project(self):
        # Saisie de l'emplacement du projet
        base_form = DataForm([['Répertoire de sortie', 'project_out_dir', 'répertoire'],
                            ['Racine Hugin', 'hugin_root', 'répertoire']])
        base_form.exec()

        # Saisie du nom du projet
        project_name, accepted = QInputDialog.getText(self, 'Nom du projet', 'Entrez le nom du projet :')

        while True:
            if accepted and project_name == '':
                QMessageBox.warning(self, 'Erreur', 'Le nom du projet ne peut pas être vide.')
                project_name, _ = QInputDialog.getText(self, 'Nom du projet', 'Entrez le nom du projet :')
            elif not accepted:
                # Afficher une boîte de dialogue pour informer l'utilisateur
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
                                            'Ce fichier existe déjà. Voulez vous écrire par dessus? Ce qu\'il contient sera effacé.',
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

        # Saisie du nombre des scans à incorporer
        num_scans, accepted = QInputDialog.getInt(self, 'Nombre de scans', 'Entrez le nombre de scans à incorporer :', 1, 1, 100)
        if not accepted:
            sys.exit()
        total_data = []
        scans_info = []

        # Pour chaque scan, on demande les informations nécessaires, puis on traite les photos
        for i in range(num_scans):
            scan_form = DataForm([['Trajectoire', 'traj_path', 'file'],
                                  ['Calibration', 'cam_cal_path', 'file'],
                                  ['Répertoire photo', 'raw_photo_dir', 'répertoire']],
                                  title = f'Scan {i+1} - Informations')
            scan_form.exec()

            scans_info.append([scan_form.paths['traj_path'], scan_form.paths['cam_cal_path'], scan_form.paths['raw_photo_dir']])
            
        for traj_path, cam_cal_path, raw_photo_dir in scans_info:
            traj_head, traj = readCSV(traj_path, ' ')
            calibration = readJSON(cam_cal_path)

            photo_info = get_valid_pairs(raw_photo_dir)
            photo_info = get_photo_locations(photo_info, traj, traj_head, calibration)

            total_data.extend(photo_info)

        stitch_photos(total_data, project_path, calibration, base_form.paths['hugin_root'])

        self.export_data(total_data, project_path)

    def add_scans(self):
        # Saisie de l'emplacement du projet
        base_form = DataForm([['Répertoire du projet', 'project_in_dir', 'répertoire'],
                            ['Racine Hugin', 'hugin_root', 'répertoire']])
        base_form.exec()

        # Saisie du nombre des scans à incorporer
        num_scans, accepted = QInputDialog.getInt(self, 'Nombre de scans', 'Entrez le nombre de scans à incorporer :', 1, 1, 100)
        if not accepted:
            sys.exit()
        new_data = []
        _, total_data = readCSV(os.path.join(base_form.paths['project_in_dir'], 'photo_info.csv'))
        new_scans_info = []

        for i in range(num_scans):
            scan_form = DataForm([['Trajectoire', 'traj_path', 'file'],
                                  ['Calibration', 'cam_cal_path', 'file'],
                                  ['Répertoire photo', 'raw_photo_dir', 'répertoire']],
                                  title = f'Scan {i+1} - Informations')
            scan_form.exec()

            new_scans_info.append([scan_form.paths['traj_path'], scan_form.paths['cam_cal_path'], scan_form.paths['raw_photo_dir']])
            
        for traj_path, cam_cal_path, raw_photo_dir in new_scans_info:
            traj_head, traj = readCSV(traj_path, ' ')
            calibration = readJSON(cam_cal_path)

            photo_info = get_valid_pairs(raw_photo_dir)
            photo_info = get_photo_locations(photo_info, traj, traj_head, calibration)

            new_data.extend(photo_info)

        stitch_photos(new_data, base_form.paths['project_in_dir'], calibration, base_form.paths['hugin_root'], index_start = len(total_data))

        total_data.extend(new_data)

        self.export_data(total_data, base_form.paths['project_in_dir'])

    def export_data(self, photo_info, project_path):
        export_photo_info_to_csv(photo_info, os.path.join(project_path, 'photo_info.csv'))

        print("Exportations CSV terminées!")
        logger.info("Exportations CSV terminées!")

app = QApplication([])
window = MainWindow()
