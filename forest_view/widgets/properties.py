from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFormLayout, QLabel, QWidget


class ProprietyWidget(QWidget):
    """
    Widget de propriétés pour afficher les informations des points d'intérêt.

    Args:
        fields (list): Liste de noms de champs à afficher.
    """
    def __init__(self, fields):
        super().__init__()
        self.inner_layout = QFormLayout()
        self.inner_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.inner_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        self.set_fields(fields)
        self.setLayout(self.inner_layout)

    def set_fields(self, fields):
        for field in fields:
            label = QLabel(f'{field} :')
            attribute = QLabel('')
            self.inner_layout.addRow(label, attribute)

    def load_data(self, data):
        """Remplit les champs avec le dictionnaire data (clés = noms de champs)."""
        for i in range(self.inner_layout.rowCount()):
            label_widget = self.inner_layout.itemAt(i, QFormLayout.ItemRole.LabelRole).widget()
            label = label_widget.text()[:-2]  # enlève " :"
            field_widget = self.inner_layout.itemAt(i, QFormLayout.ItemRole.FieldRole).widget()
            if label in data:
                field_widget.setText(str(data[label]))
            else:
                field_widget.setText('ND')

    def reset(self):
        while self.inner_layout.rowCount():
            self.inner_layout.removeRow(0)
