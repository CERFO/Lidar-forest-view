import os
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QEvent, QStandardPaths
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QToolTip,
    QVBoxLayout,
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
        self.settings_path = self._resolve_settings_path()
        self.memory = self._load_settings()
        self._instant_tooltip = {}

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

    def _resolve_settings_path(self):
        config_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
        if not config_dir:
            return Path('appsettings.json')
        config_path = Path(config_dir)
        config_path.mkdir(parents=True, exist_ok=True)
        return config_path / 'appsettings.json'

    def _load_settings(self):
        if self.settings_path.exists():
            return readJSON(self.settings_path)
        legacy_path = Path('appsettings.json')
        if legacy_path.exists():
            return readJSON(legacy_path)
        return {}

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
            info.setStyleSheet("")
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
            writeJSON(self.settings_path, self.memory)
            self.accept()
            self.close()
        else:
            QMessageBox.warning(
                self, 'Champs incomplets',
                'Tous les champs doivent être remplis pour soumettre'
            )

    def closeEvent(self, event):
        """Gère la fermeture par le X : quitte l'app si aucun chemin valide (sauf en mode « Changer de site »)."""
        if getattr(self, '_change_site_context', False):
            event.accept()
            return
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

class NewTreeForm(QDialog):
    def __init__(self, parent, fields, tree_number):
        super().__init__(parent)

        self.tree_location = [None, None, None]
        self.tree_data = dict.fromkeys(fields if len(fields) != 0 else ['No_tige'], '')
        self.tree_data.update({'No_tige': int(tree_number)})
        self.submitted = False

        self.setWindowTitle('Nouvel arbre')
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Dialog
            | Qt.WindowType.WindowCloseButtonHint
        )

        if hasattr(self.parent(), 'new_tree_pos_requested'):
            self.parent().new_tree_pos_requested.emit(True, self.set_tree_location)

        layout = QFormLayout(self)
        for field, value in self.tree_data.items():
            line_edit = QLineEdit(str(value) if value is not None else '', self)
            line_edit.textChanged.connect(
                lambda text, f=field: self.tree_data.update({f:text})
            )
            layout.addRow(field, line_edit)
        submit_button = QPushButton("Soumettre")
        submit_button.clicked.connect(self.submit_data)
        layout.addRow(submit_button)

    def set_tree_location(self, location):
        self.tree_location = location

    def submit_data(self):
        if all(coord is not None for coord in self.tree_location) and self.tree_data.get('No_tige') != '':
            if hasattr(self.parent(), 'new_tree_pos_requested'):
                self.parent().new_tree_pos_requested.emit(False, self.set_tree_location)
            self.submitted = True
            self.accept()
        else:
            QMessageBox.information(self, 'Incomplet', 'Un arbre doit minimalement avoir une position et un numéro')

    def get_data(self):
        if self.submitted:
            data = {k:v for k, v in zip(['x','y','z'],self.tree_location)}
            data.update(self.tree_data)
            return data
        else:
            return None
        
    def closeEvent(self, event):
        if hasattr(self.parent(), 'new_tree_pos_requested') and not self.submitted:
            self.parent().new_tree_pos_requested.emit(False, self.set_tree_location)
        return super().closeEvent(event)
    
class CheckBoxChoiceForm(QDialog):
    def __init__(self, parent, choices):
        super().__init__(parent)

        self.setWindowTitle('Champs à retirer')
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Dialog
            | Qt.WindowType.WindowCloseButtonHint
        )

        self.choice_dict = dict.fromkeys(choices, False)
        layout = QVBoxLayout(self)
        for choice in choices:
            cb = QCheckBox(choice, self)
            cb.setChecked(False)
            cb.clicked.connect(lambda state, c=choice: self.choice_dict.update({c:state}))
            layout.addWidget(cb)
        submit_button = QPushButton("Soumettre")
        submit_button.clicked.connect(self.submit_choice)
        layout.addWidget(submit_button)

    def submit_choice(self):
        self.accept()

    def get_choices(self):
        return self.choice_dict

class SurfaceColumnForm(QDialog):
    """Permet de sélectionner la colonne et l'unité pour le DHP ou la surface terrière"""
    def __init__(self, choices:list[str], parent=None):
        super().__init__(parent)

        self.setWindowTitle('Colonne de surface terrière')
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Dialog
            | Qt.WindowType.WindowCloseButtonHint
        )

        layout = QVBoxLayout(self)
        layout.setVerticalSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.col_type = QComboBox()
        self.col_type.addItems(['Surface terrière', 'DHP'])
        self.col_type.currentTextChanged.connect(self._on_type_change)
        layout.addWidget(self.col_type)
        self.col_name = QComboBox(self)
        self.col_name.addItems(choices)
        layout.addWidget(self.col_name)
        self.units_ST = QComboBox()
        self.units_ST.addItems(['m²', 'cm²', 'mm²'])
        layout.addWidget(self.units_ST)
        self.units_DBH = QComboBox()
        self.units_DBH.addItems(['m', 'cm', 'mm'])
        self.units_DBH.setVisible(False)
        layout.addWidget(self.units_DBH)
        self.new_col_label = QLabel('Nouvelle colonne')
        self.new_col_label.setVisible(False)
        layout.addWidget(self.new_col_label)
        self.new_col_name = QLineEdit('ST')
        self.new_col_name.setVisible(False)
        layout.addWidget(self.new_col_name)
        submit_button = QPushButton("Soumettre")
        submit_button.clicked.connect(self.submit_choice)
        layout.addWidget(submit_button)

    def _on_type_change(self, new_text):
        self.units_ST.setVisible(new_text == 'Surface terrière')
        self.units_DBH.setVisible(new_text == 'DHP')
        self.new_col_label.setVisible(new_text == 'DHP')
        self.new_col_name.setVisible(new_text == 'DHP')
        self.adjustSize()

    def submit_choice(self):
        self.accept()

    def get_choices(self):
        if self.col_type.currentText() == 'Surface terrière':
            return self.col_type.currentText(), [self.col_name.currentText(), self.units_ST.currentText()]

        if self.col_type.currentText() == 'DHP':
            return self.col_type.currentText(), [self.col_name.currentText(), self.units_DBH.currentText(), self.new_col_name.text()]


