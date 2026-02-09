import os
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
)

from forest_view.io import readJSON, writeJSON


class DataForm(QDialog):
    """
    Formulaire de saisie de chemins d'accès vers des fichiers ou des répertoires.

    Args:
        fields (list): Liste de tuples (texte du label, nom du champ, type: 'file' ou 'répertoire').
        title (str): Titre de la fenêtre du formulaire.
    """
    def __init__(self, fields, title="Saisie des chemins d'accès"):
        super().__init__()
        self.setWindowTitle(title)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)

        self.fields = {}
        self.paths = {}
        self.memory = readJSON('memory.json') if os.path.exists('memory.json') else {}

        self.layout = QFormLayout()
        for text, field, path_type in fields:
            self.add_field(text, field, path_type)

        self.submit_button = QPushButton("Soumettre")
        self.submit_button.clicked.connect(self.submit_data)
        self.layout.addRow(self.submit_button)
        self.setLayout(self.layout)

    def add_field(self, label_text, field_name, path_type):
        """Ajoute un champ de saisie avec label et bouton Parcourir."""
        inner_layout = QHBoxLayout()
        line_edit = QLineEdit(text=self.memory.get(field_name, ''))
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(lambda checked, le=line_edit: self.browse_file(le, label_text, path_type))
        inner_layout.addWidget(line_edit)
        inner_layout.addWidget(browse_button)
        self.layout.addRow(label_text, inner_layout)
        self.fields[field_name] = line_edit

    def browse_file(self, line_edit, caption, path_type):
        """Ouvre une boîte de dialogue pour sélectionner un fichier ou un répertoire."""
        if path_type == 'file':
            file_path, _ = QFileDialog.getOpenFileName(self, f'Sélectionnez {caption}')
        elif path_type == 'répertoire':
            file_path = QFileDialog.getExistingDirectory(self, f'Sélectionnez {caption}')
        else:
            file_path = ''
        if file_path:
            line_edit.setText(file_path)

    def submit_data(self):
        """Valide les champs, enregistre dans self.paths et self.memory, écrit memory.json."""
        self.paths.clear()
        if all(value.text() != '' for value in self.fields.values()):
            for field_name, line_edit in self.fields.items():
                self.paths[field_name] = line_edit.text()
                self.memory[field_name] = line_edit.text()
            writeJSON('memory.json', self.memory)
            self.close()
        else:
            QMessageBox.warning(
                self, 'Champs incomplets',
                'Tous les champs doivent être remplis pour soumettre'
            )

    def closeEvent(self, event):
        """Gère la fermeture par le X : quitte l'app si aucun chemin valide."""
        if self.paths and all(value != '' for value in self.paths.values()):
            event.accept()
        else:
            reply = QMessageBox.question(
                self, 'Vous partez déjà?',
                'Êtes-vous sûr de vouloir quitter?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                event.accept()
                sys.exit()
            else:
                event.ignore()
