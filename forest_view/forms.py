import os
import sys

from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QToolTip,
    QWidget,
)

from forest_view.io import readJSON, writeJSON


class DataForm(QDialog):
    """
    Formulaire de saisie de chemins d'accès vers des fichiers ou des répertoires.

    Paramètres:
        fields (list): Liste de tuples (texte du label, nom du champ, type).
            type : 'file' ou 'répertoire'. L'aide (infobulle ⓘ) est chargée depuis
            forest_view/field_hints.json selon le nom du champ.
        title (str): Titre de la fenêtre du formulaire.
    """
    def __init__(self, fields, title="Saisie des chemins d'accès"):
        super().__init__()
        self.setWindowTitle(title)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Dialog
            | Qt.WindowType.WindowCloseButtonHint
        )

        self.fields = {}
        self.paths = {}
        self.memory = readJSON('appsettings.json') if os.path.exists('appsettings.json') else {}
        self._instant_tooltip = {}  # id(widget) -> texte d'aide, pour affichage immédiat au survol

        _hints_path = os.path.join(os.path.dirname(__file__), 'field_hints.json')
        self._field_hints = readJSON(_hints_path) if os.path.exists(_hints_path) else {}

        self.layout = QFormLayout()
        for item in fields:
            text, field_name, path_type = item[0], item[1], item[2]
            help_text = self._field_hints.get(field_name)
            self.add_field(text, field_name, path_type, help_text)

        self.submit_button = QPushButton("Soumettre")
        self.submit_button.clicked.connect(self.submit_data)
        self.layout.addRow(self.submit_button)
        self.setLayout(self.layout)

    def add_field(self, label_text, field_name, path_type, help_text=None):
        """Ajoute un champ de saisie avec label, optionnellement une infobulle au survol, et bouton Parcourir."""
        label_widget = QWidget()
        label_layout = QHBoxLayout(label_widget)
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.setSpacing(4)
        lbl = QLabel(label_text)
        label_layout.addWidget(lbl)
        if help_text:
            info = QLabel("ⓘ")
            info.setToolTip(help_text)
            info.setCursor(Qt.CursorShape.WhatsThisCursor)
            font = QFont(info.font())
            font.setPointSize(font.pointSize() - 1)
            info.setFont(font)
            info.setStyleSheet("")  # utilise la couleur de texte du thème (blanc sur fond sombre, noir sur clair)
            self._instant_tooltip[id(info)] = help_text
            info.installEventFilter(self)
            label_layout.addWidget(info)
        label_layout.addStretch()

        inner_layout = QHBoxLayout()
        line_edit = QLineEdit(text=self.memory.get(field_name, ''))
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(lambda checked, le=line_edit: self.browse_file(le, label_text, path_type))
        inner_layout.addWidget(line_edit)
        inner_layout.addWidget(browse_button)
        self.layout.addRow(label_widget, inner_layout)
        self.fields[field_name] = line_edit

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Enter and id(obj) in self._instant_tooltip:
            QToolTip.showText(QCursor.pos(), self._instant_tooltip[id(obj)])
        elif event.type() == QEvent.Type.Leave and id(obj) in self._instant_tooltip:
            QToolTip.hideText()
        return super().eventFilter(obj, event)

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
        """Valide les champs, enregistre dans self.paths et self.memory, écrit appsettings.json."""
        self.paths.clear()
        if all(value.text() != '' for value in self.fields.values()):
            for field_name, line_edit in self.fields.items():
                self.paths[field_name] = line_edit.text()
                self.memory[field_name] = line_edit.text()
            writeJSON('appsettings.json', self.memory)
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
