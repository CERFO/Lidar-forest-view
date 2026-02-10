from Librairie import *
import shutil

from forest_view.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

class MainWindow(QWidget):
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
            scan_form = DataForm([['GS-Vision', 'gs_vision_path', 'file'],
                                ['Photos panoramiques', 'panoramic_photos_dir', 'répertoire']],
                                title = f'Scan {i+1} - Informations')
            scan_form.exec()

            scans_info.append([scan_form.paths['gs_vision_path'], scan_form.paths['panoramic_photos_dir']])
        
        index = 0
        for gs_vision_path, photo_dir in scans_info:
            gs_vision = readJSON(gs_vision_path)
            gs_vision_data = gs_vision['images']

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
                total_data.append(entry)

                src_path = os.path.join(photo_dir, data['imagePath'][2:])
                dst_path = os.path.join(project_path, 'panoramas', entry_name)
                index += 1
                shutil.copy2(src_path, dst_path)

        self.export_data(total_data, project_path)

    def add_scans(self):
         # Saisie de l'emplacement du projet
        base_form = DataForm([['Répertoire du projet', 'project_in_dir', 'répertoire']])
        base_form.exec()

        # Saisie du nombre des scans à incorporer
        num_scans, _ = QInputDialog.getInt(self, 'Nombre de scans', 'Entrez le nombre de scans à incorporer :', 1, 1, 100)
        _, total_data = readCSV(os.path.join(base_form.paths['project_in_dir'], 'photo_info.csv'))
        scans_info = []

        for i in range(num_scans):
            scan_form = DataForm([['GS-Vision', 'gs_vision_path', 'file'],
                                  ['Photos panoramiques', 'panoramic_photos_dir', 'répertoire']],
                                  title = f'Scan {i+1} - Informations')
            scan_form.exec()

            scans_info.append([scan_form.paths['gs_vision_path'], scan_form.paths['panoramic_photos_dir']])

        index = len(total_data)
        for i, photo_dir, gs_vision_path in enumerate(scans_info):
            gs_vision = readJSON(gs_vision_path)
            gs_vision_data = gs_vision['images']

            for data in gs_vision_data:
                entry_name = f'pano{i+index:04d}.jpg'
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
                total_data.append(entry)

                src_path = os.path.join(photo_dir, data['imagePath'][2:])
                dst_path = os.path.join(base_form.paths['project_in_dir'], 'panoramas', entry_name)
                index += 1
                shutil.copy2(src_path, dst_path)
            
        self.export_data(total_data, base_form.paths['project_in_dir'])

    def export_data(self, photo_info, project_path):
        export_photo_info_to_csv(photo_info, os.path.join(project_path, 'photo_info.csv'))

        print("Exportations CSV terminées!")
        logger.info("Exportations CSV terminées!")

app = QApplication([])
window = MainWindow()
