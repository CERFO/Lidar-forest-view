from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget, QGridLayout, QLabel, QDialog

from forest_view.forms import SurfaceColumnForm
from forest_view.widgets import ProprietyWidget

CONVERSION_FACTORS = {'m': 1, 'cm': 100, 'mm': 1000,
                      'm²': 1, 'cm²': 1e4, 'mm²': 1e6}

class TreeMarkerWidget(QWidget):
    """ Widget gérant la sélection de tiges pour le martelage"""
    # Signaux
    tree_selection_changed = pyqtSignal()

    def __init__(self, propriety_widget:ProprietyWidget, parent=None):
        super().__init__(parent)

        self.propriety_widget = propriety_widget
        self.table = propriety_widget.table
        
        form = SurfaceColumnForm(self.propriety_widget._fields, self)
        if form.exec() != QDialog.DialogCode.Accepted:
                self.deleteLater()
                return
        
        type, info = form.get_choices()
        if type == "Surface terrière":
            self.surface_col = info[0]
            self.conversion = CONVERSION_FACTORS[info[1]]
        elif type == "DHP":
            self.propriety_widget.add_col(info[2])
            self.surface_col = info[2]
            dbh_col = self.propriety_widget.get_col_from_header(info[0])
            surf_col = self.propriety_widget.get_col_from_header(self.surface_col)
            # Calcul des surfaces par arbre
            for row in range(self.table.rowCount()):
                dbh = self.table.item(row, dbh_col).text()
                surf = self.calculate_surface(dbh, info[1])
                if surf:
                    surf_item = self.table.item(row, surf_col)
                    surf_item.setText(str(surf))
            self.conversion = 1
            
        self.total_tree_n = self.table.rowCount()
        self.selected_tree_n = int(0)
        self.selected_tree_ratio = float(0)

        # Calcul de la surface totale
        col = self.propriety_widget.get_col_from_header(self.surface_col)
        texts = [
            self.table.item(row, col).text()
            for row in range(self.table.rowCount())
            if self.table.item(row, col) is not None
        ]

        self.total_surface = sum([float(text) / self.conversion for text in texts if self.is_float(text)])
        self.selected_surface = float(0)
        self.selected_surface_ratio = float(0)

        layout = QGridLayout(self)
        for i, (label, value) in enumerate(zip(("Nb d'arbres sélectionnés", "Nb d'arbres total", "Surface terrière sélectionnée", "Surface terrière totale"),
                                               (self.selected_tree_n, self.total_tree_n, self.selected_surface, self.total_surface))):
            layout.addWidget(QLabel(f"{label} : "), i, 0, 1, 1, Qt.AlignmentFlag.AlignRight)
            fmt = ".0f" if isinstance(value, int) else ".2f"
            unit = "" if isinstance(value, int) else " m²"
            layout.addWidget(QLabel(f"{value:{fmt}}{unit}"), i, 1, 1, 1, Qt.AlignmentFlag.AlignLeft)

        for i, value in enumerate((self.selected_tree_ratio, self.selected_surface_ratio)):
            layout.addWidget(QLabel(f"{value * 100:.1f} %"), 2*i, 2, 2, 1)

    def on_selection_change(self):
        # Transmettre sélections à la carte
        # Transmettre sélections à la fenêtre lidar????
        # Ajustement de la surface terrière
        # Transmission des signaux pour le changement de couleur et le retrait des qsm
        pass

    def add_selection_col(self):
        # Ajouter une colonne de sélection à la table d'attributs
            # Elle doit toujours être la dernière (même si on ajoute des colonnes)
        # Pourait être implémenté dans ProprietyWidget
        pass

    @staticmethod
    def is_float(value):
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
        
    @staticmethod
    def calculate_surface(dbh:float | int | str, unit:str) -> float | None:
        """Renvoie la surface terrière d'un arbre en mètres carrés"""
        if TreeMarkerWidget.is_float(dbh):
            surf = (float(dbh) / CONVERSION_FACTORS[unit])**2 * 3.14 / 4
            return surf
        return
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(180, 180, 180, 150))
        painter.drawRoundedRect(self.rect(), 8, 8)
        return super().paintEvent(event)

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication([])
    widget = TreeMarkerWidget()
    widget.show()
    app.exec()