from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHeaderView,
    QInputDialog,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from forest_view.utils import _tree_data_match
from forest_view.forms import NewTreeForm, CheckBoxChoiceForm


class ProprietyWidget(QWidget):
    """
    Table d'attributs pour afficher les informations des points d'intérêt (ex. arbres).
    Colonnes = noms de champs. Une case « Afficher uniquement la ligne sélectionnée » filtre les lignes.
    Clic sur un arbre dans la carte → surligne la ligne ; sélection d'une ligne → surligne l'arbre sur la carte.
    """
    tree_row_selected = pyqtSignal(object)
    tree_data_changed = pyqtSignal(object)
    new_tree_pos_requested = pyqtSignal(bool, object)
    new_tree = pyqtSignal(list, list)
    new_tree_position = pyqtSignal(object, object)
    saved_data = pyqtSignal(list)
    row_removed = pyqtSignal(object)
    col_removed = pyqtSignal(str)

    mark_tree = pyqtSignal(object, bool)

    def __init__(self, fields):
        super().__init__()
        self._fields = []
        self._all_data = []
        self._selecting_programmatically = False
        self._filter_only_selected = False
        self._changes_made = False
        self._editing = False
        self._check_cols = []
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table)
        self.set_fields(fields)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

    def get_field_names(self):
        """Noms des colonnes (champs) actuels, pour export CSV lorsque la table est vide."""
        return list(self._fields)

    @staticmethod
    def _next_no_tige(all_data):
        best = 0.0
        found = False
        for d in all_data:
            v = d.get('No_tige')
            if v is None or v == '':
                continue
            try:
                val = float(v)
            except (TypeError, ValueError):
                continue
            found = True
            best = max(best, val)
        return int(best) + 1 if found else 1

    def set_filter_only_selected(self, on):
        """Active ou désactive le filtre « afficher uniquement la ligne sélectionnée » (appelé par la case à cocher)."""
        self._filter_only_selected = bool(on)
        self._apply_filter()

    def set_fields(self, fields):
        """Définit les colonnes (noms des champs)."""
        self._fields = list(fields) if fields else []
        self._all_data = []
        self.table.setColumnCount(len(self._fields))
        self.table.setRowCount(0)
        if self._fields:
            self.table.setHorizontalHeaderLabels(self._fields)

    def load_all_data(self, list_of_dicts):
        """Remplit la table avec tous les enregistrements (ex. tous les arbres du CSV)."""
        if not self._fields or not list_of_dicts:
            return
        self._selecting_programmatically = True
        try:
            self._all_data = []
            self.table.setRowCount(len(list_of_dicts))
            for row, entry in enumerate(list_of_dicts):
                tree_data = {k: v for k, v in entry.items() if k not in {'x', 'y', 'z'}}
                self._all_data.append(entry)
                for col, field in enumerate(self._fields):
                    value = tree_data.get(field, 'ND')
                    item = QTableWidgetItem(str(value))
                    self.table.setItem(row, col, item)
            self._apply_filter()
        finally:
            self._selecting_programmatically = False

    def _apply_filter(self):
        """Si le filtre est actif, masque les lignes non sélectionnées."""
        if self._filter_only_selected:
            selected_row = self.table.currentRow()
            for row in range(self.table.rowCount()):
                self.table.setRowHidden(row, row != selected_row)
        else:
            for row in range(self.table.rowCount()):
                self.table.setRowHidden(row, False)

    def load_data(self, data:dict, row = None):
        """Ajoute ou met à jour une ligne avec le dictionnaire data (clés = noms de champs).
        Row = int: ligne à éditer ou None: ajout d'une ligne"""
        self._selecting_programmatically = True
        if not self._fields and self.table.rowCount() == 0:
            self._fields = [key for key in data.keys() if key not in ['x', 'y', 'z']]
            self.table.setColumnCount(len(self._fields))
            self.table.setHorizontalHeaderLabels(self._fields)
        if row is None or row >= self.table.rowCount():
            self._all_data.append(data)
            row = self.table.rowCount()
            self.table.setRowCount(self.table.rowCount() + 1)
        for col, field in enumerate(self._fields):
            value = data.get(field, 'ND')
            item = QTableWidgetItem(str(value))
            self.table.setItem(row, col, item)
        self._selecting_programmatically = False

    def select_row_for_tree(self, tree_data):
        """Sélectionne et met en surbrillance la ligne correspondant à tree_data (émet par la carte)."""
        if not tree_data or self._selecting_programmatically:
            return
        for row, data in enumerate(self._all_data):
            if _tree_data_match(data, tree_data):
                self._selecting_programmatically = True
                try:
                    self.table.clearSelection()
                    self.table.selectRow(row)
                    self.table.scrollTo(self.table.model().index(row, 0))
                    self._apply_filter()
                finally:
                    self._selecting_programmatically = False
                break

    def _on_selection_changed(self):
        if self._selecting_programmatically or not self._all_data:
            return
        self._apply_filter()
        row = self.table.currentRow()
        if 0 <= row < len(self._all_data):
            self.tree_row_selected.emit((row, self._all_data[row]))

    def toggle_edition(self, on):
        self._editing = on
        if on:
            self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
            self.table.cellChanged.connect(self._on_cell_changed)
        else:
            self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            try:
                self.table.cellChanged.disconnect(self._on_cell_changed)
            except (TypeError, RuntimeError):
                pass

    def _on_cell_changed(self, row, col):
        self._all_data[row][self.table.horizontalHeaderItem(col).text()] = self.table.item(row,col).text()
        changed_line = [
            [
                self.table.horizontalHeaderItem(c).text(),
                self.table.item(row, c).text()
                if self.table.item(row, c) is not None
                else None,
            ]
            for c in range(self.table.columnCount())
            if c not in self._check_cols
        ]
        self.tree_data_changed.emit((row, {k:v for k, v in changed_line}))
        self._changes_made = True

    def _on_item_change(self, item):
        if item.column() not in self._check_cols:
            return
        
        row = item.row()
        changed_line = [
            [
                self.table.horizontalHeaderItem(c).text(),
                self.table.item(row, c).text()
                if self.table.item(row, c) is not None
                else None,
            ]
            for c in range(self.table.columnCount())
            if c not in self._check_cols
        ]

        self.mark_tree.emit((row, {k:v for k, v in changed_line}), item.checkState() == Qt.CheckState.Checked)

    def add_col(self, new_col_name = None):
        """ Ajoute une colonne d'un nom choisi """
        if not new_col_name and self._editing:
            new_col_name, accepted = QInputDialog.getText(self, 'Nom du champ', 'Champ')
            if not accepted:
                return
        elif not new_col_name:
            return
        
        self._fields.append(new_col_name)

        col_idx = self.table.columnCount()
        if col_idx - 1 in self._check_cols:
            col_idx = min(self._check_cols)
            self._check_cols = [col + 1 for col in self._check_cols]

        self.table.insertColumn(col_idx)
        self.table.setHorizontalHeaderItem(col_idx, QTableWidgetItem(new_col_name))
        for entry in self._all_data:
            entry[new_col_name] = ''
        for row in range(self.table.rowCount()):
            self.table.setItem(row, col_idx, QTableWidgetItem(str()))

    def add_selection_col(self, new_col_name):
        self.table.insertColumn(self.table.columnCount())
        col_idx = self.table.columnCount()-1
        self._check_cols.append(col_idx) # NOTE : fragile à la modification des colonnes. Modifier les insertions et délétions de colonnes pour que tout fonctionne
        self.table.setHorizontalHeaderItem(col_idx, QTableWidgetItem(new_col_name))
        for row in range(self.table.rowCount()):
            item = QTableWidgetItem()
            item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable |
                Qt.ItemFlag.ItemIsEnabled
            )
            item.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(row, col_idx, item)

        self.table.itemChanged.connect(self._on_item_change)

    def add_tree(self):
        """ Appel le formulaire pour les nouveaux arbres """
        if self._editing:
            next_no = 1 if len(self._all_data) == 0 else self._next_no_tige(self._all_data)
            form = NewTreeForm(self, self._fields, next_no)
            form.accepted.connect(lambda: self._dispatch_new_tree_data(form.get_data()))
            form.show()

    def _dispatch_new_tree_data(self, data):
        """ Suite de add_tree. Ajoute la donnée à la table et à _all_data. Émet la nouvelle donnée"""
        if data is None:
            return
        self.new_tree.emit([data], [self.table.rowCount()])
        self.new_tree_position.emit([data.get(coord) for coord in ['x','y','z']], data.get('No_tige'))
        self.load_data(data)
        self._changes_made = True
    
    def on_save(self):
        """ Émet les modifications """
        if self._changes_made:
            self.saved_data.emit(self._all_data)
            self._changes_made = False

    def get_col_from_header(self, header:str):
        for i in range(self.table.columnCount()):
            item = self.table.horizontalHeaderItem(i)
            if item and item.text() == header:
                return i
        return None

    def remove_col(self):
        if not self._editing and self.table.columnCount() == 0:
            return
        form = CheckBoxChoiceForm(self, self._fields)
        if form.exec() != QDialog.DialogCode.Accepted:
            return
        to_remove = [field for field, remove in form.get_choices().items() if remove is True]
        if not to_remove:
            return
        confirm = QMessageBox.question(
            self,
            'Confirmer',
            'Retirer les champs sélectionnés des arbres ? Cette action est irréversible sans recharger les données.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        
        self._check_cols = [col - 1 for col in self._check_cols]

        for field in to_remove:
            self._fields.remove(field)
            for entry in self._all_data:
                entry.pop(field, None)
            for col in range(self.table.columnCount()):
                if self.table.horizontalHeaderItem(col).text() == field:
                    self.table.removeColumn(col)
                    break
            self.col_removed.emit(field)
        self._changes_made = True

    def delete_current_line(self):
        """ Retire la ligne sélectionnée, stock sont index, puis émet la donnée """
        if self._editing and self.table.currentRow() != -1:
            confirm = QMessageBox.question(
                self,
                'Confirmer',
                'Supprimer la ligne sélectionnée ? Cette action est irréversible sans recharger les données.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
            row = self.table.currentRow()
            self.table.removeRow(row)
            tree_data = self._all_data[row]
            del self._all_data[row]
            self.row_removed.emit((row, tree_data))
            self._changes_made = True

    def reset(self):
        """Vide les lignes en gardant les en-têtes de colonnes."""
        self._all_data = []
        self._filter_only_selected = False
        self._changes_made = False
        self._editing = False
        self.table.setRowCount(0)
