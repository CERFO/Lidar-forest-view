from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget, QGridLayout, QLabel, QDialog

from forest_view.forms import SurfaceColumnForm
from forest_view.widgets import ProprietyWidget

CONVERSION_FACTORS = {'m': 1, 'cm': 100, 'mm': 1000,
                      'm²': 1, 'cm²': 1e4, 'mm²': 1e6,
                      'm³': 1, 'cm³': 1e6, 'mm³': 1e9}

class TreeMarkerWidget(QWidget):
    """ Widget gérant la sélection de tiges pour le martelage"""
    tree_selection_changed = pyqtSignal()

    @classmethod
    def from_form(cls, propriety_widget:ProprietyWidget, parent = None):
        form = SurfaceColumnForm(propriety_widget._fields)
        if form.exec() != QDialog.DialogCode.Accepted:
                return None
        
        col_dict = form.get_choices()

        return cls(propriety_widget, col_dict, parent)

    def __init__(self, propriety_widget:ProprietyWidget, col_dict : dict = None, parent=None):
        super().__init__(parent)

        self.propriety_widget = propriety_widget
        self.table = propriety_widget.table
        self._counter = 0
        self.col_dict = col_dict

        for key, info in self.col_dict.items():
            if 'units' in info:
                self.col_dict[key]['conversion'] = CONVERSION_FACTORS[info['units']]
        
        if self.col_dict['surface']['col'] not in self.propriety_widget._fields:
            new_col_name = self.col_dict['surface']['col']
            self.propriety_widget.add_col(new_col_name)
            dbh_col = self.propriety_widget.get_col_from_header(self.col_dict['dbh']['col'])
            surf_col = self.propriety_widget.get_col_from_header(new_col_name)
            # Calcul des surfaces par arbre
            for row in range(self.table.rowCount()):
                dbh = self.table.item(row, dbh_col).text()
                surf = self.calculate_surface(dbh, self.col_dict['dbh']['units'])
                if surf:
                    surf_item = self.table.item(row, surf_col)
                    surf_item.setText(str(surf))
            self.col_dict['surface']['conversion'] = 1
            
        self.total_tree_n = self.table.rowCount()
        self.selected_tree_n = int(0)
        self.selected_tree_ratio = float(0)

        # Calcul de la surface totale
        col = self.propriety_widget.get_col_from_header(self.col_dict['surface']['col'])
        texts = [
            self.table.item(row, col).text()
            for row in range(self.table.rowCount())
            if self.table.item(row, col) is not None
        ]

        self.total_surface = sum([float(text) / self.col_dict['dbh']['conversion'] for text in texts if self.is_float(text)])
        self.selected_surface = float(0)
        self.selected_surface_ratio = float(0)

        self.propriety_widget.add_selection_col('Martelage')

        layout = QGridLayout(self)
        for i, (label, value) in enumerate(zip(("Nb d'arbres sélectionnés", "Nb d'arbres total", "Surface terrière sélectionnée", "Surface terrière totale"),
                                               (self.selected_tree_n, self.total_tree_n, self.selected_surface, self.total_surface))):
            layout.addWidget(QLabel(f"{label} : "), i, 0, 1, 1, Qt.AlignmentFlag.AlignRight)
            fmt = ".0f" if isinstance(value, int) else ".2f"
            unit = "" if isinstance(value, int) else " m²"
            layout.addWidget(QLabel(f"{value:{fmt}}{unit}"), i, 1, 1, 1, Qt.AlignmentFlag.AlignLeft)

        for i, value in enumerate((self.selected_tree_ratio, self.selected_surface_ratio)):
            layout.addWidget(QLabel(f"{value * 100:.1f} %"), 2*i, 2, 2, 1)

    def on_selection_change(self, payload, marked):
        """Calcul et met à jour les valeurs des paramètres suite à une modification de sélection"""
        _, data = payload
        surface = float(data[self.col_dict['surface']['col']]) if self.is_float(data[self.col_dict['surface']['col']]) else 0
        
        self._counter += 1
        if self._counter % 50 == 0: # NOTE : pas certain que ce soit nécessaire
            select_col = self.propriety_widget.get_col_from_header('Martelage')
            surf_col = self.propriety_widget.get_col_from_header(self.col_dict['surface']['col'])
            selection = [
                self.table.item(row, select_col).checkState() == Qt.CheckState.Checked
                for row in range(self.table.rowCount())
            ]
            texts = [
                self.table.item(row, surf_col).text()
                for row in range(self.table.rowCount())
                if self.table.item(row, surf_col) is not None
            ]
            self.selected_tree_n = sum(selection)
            self.selected_surface = sum([float(text) / self.col_dict['dbh']['conversion'] for text, selected in zip(texts, selection) if self.is_float(text) and selected])
        elif marked:
            self.selected_tree_n += 1
            self.selected_surface += surface
        else:
            self.selected_tree_n -= 1
            self.selected_surface -= surface
        self._calculate_ratios()
        self._update_data()

    def _calculate_ratios(self):
        self.selected_tree_ratio = self.selected_tree_n / self.total_tree_n
        self.selected_surface_ratio = self.selected_surface / self.total_surface

    def _update_data(self):
        """Met à jour la donnée dans la mise en page du widget"""
        layout = self.layout()
        for i, value in enumerate((self.selected_tree_n, self.total_tree_n, self.selected_surface, self.total_surface)):
            fmt = ".0f" if isinstance(value, int) else ".2f"
            unit = "" if isinstance(value, int) else " m²"
            layout.itemAtPosition(i,1).widget().setText(f"{value:{fmt}}{unit}")

        for i, value in enumerate((self.selected_tree_ratio, self.selected_surface_ratio)):
            layout.itemAtPosition(2*i,2).widget().setText(f"{value * 100:.1f} %")

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
        assert unit in CONVERSION_FACTORS, 'Unité non reconnue'
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
    
class ExtendedMarkingStatsWidget(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)
