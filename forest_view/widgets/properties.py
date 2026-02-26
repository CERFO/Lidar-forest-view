from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget


class ProprietyWidget(QWidget):
    """
    Table d'attributs pour afficher les informations des points d'intérêt (ex. arbres).
    Colonnes = noms de champs, lignes = enregistrements.
    """
    def __init__(self, fields):
        super().__init__()
        self._fields = []
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table)
        self.set_fields(fields)

    def set_fields(self, fields):
        """Définit les colonnes (noms des champs)."""
        self._fields = list(fields) if fields else []
        self.table.setColumnCount(len(self._fields))
        self.table.setRowCount(0)
        if self._fields:
            self.table.setHorizontalHeaderLabels(self._fields)

    def load_data(self, data):
        """Ajoute ou met à jour une ligne avec le dictionnaire data (clés = noms de champs)."""
        if not self._fields:
            return
        self.table.setRowCount(1)
        for col, field in enumerate(self._fields):
            value = data.get(field, 'ND')
            item = QTableWidgetItem(str(value))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(0, col, item)

    def reset(self):
        """Vide les lignes en gardant les en-têtes de colonnes."""
        self.table.setRowCount(0)
