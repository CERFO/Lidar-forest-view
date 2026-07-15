from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget, QGridLayout, QLabel, QDialog

from forest_view.forms import SurfaceColumnForm
from forest_view.widgets import ProprietyWidget

CONVERSION_FACTORS = {
    "m": 1,
    "cm": 100,
    "mm": 1000,
    "m²": 1,
    "cm²": 1e4,
    "mm²": 1e6,
    "m³": 1,
    "cm³": 1e6,
    "mm³": 1e9,
}

MERCHANTABLE_DBH_LIM = 0.2


class TreeMarkerWidget(QWidget):
    """Widget gérant la sélection de tiges pour le martelage

    Paramètres
    col_dict : dictionnaire de la structure suivante
        {'dbh' : {'col': , 'units':},
        'surface' : {'col': , 'units':},
        'volume' : {'col': , 'units':},}
    """

    tree_selection_changed = pyqtSignal()

    def __init__(self, propriety_widget: ProprietyWidget, col_dict: dict, parent=None):
        super().__init__(parent)

        self.propriety_widget = propriety_widget
        self.table = propriety_widget.table
        self._counter = 0
        self.col_dict = col_dict

        self.data = dict.fromkeys(col_dict.keys())
        for key in self.data.keys():
            self.data[key] = {"selected": 0, "merchantable": 0, "total": 0, "ratio": 0}
        self.data.update({"n": {"merchantable": 0, "total": 0},
                          "aire_ha": None})  # TODO : trouver comment calculer la surface de la placette

        # Ajout des facteurs conversions
        for key, info in self.col_dict.items():
            if "units" in info:
                self.col_dict[key]["conversion"] = CONVERSION_FACTORS[info["units"]]

        # Calcul des surfaces terrières
        if self.col_dict["surface"]["col"] not in self.propriety_widget._fields:
            new_col_name = self.col_dict["surface"]["col"]
            self.propriety_widget.add_col(new_col_name)
            dbh_col = self.propriety_widget.get_col_from_header(
                self.col_dict["dbh"]["col"]
            )
            surf_col = self.propriety_widget.get_col_from_header(new_col_name)

            for i in range(self.table.rowCount()):
                dbh = self.table.item(i, dbh_col).text()
                surf = self.calculate_surface(dbh, self.col_dict["dbh"]["units"])
                if surf:
                    surf_item = self.table.item(i, surf_col)
                    surf_item.setText(str(surf))
            self.col_dict["surface"]["conversion"] = 1

        # Calcul de self.data
        self.update_data()

        self.propriety_widget.add_selection_col("Martelage")

        # Mise en forme
        layout = QGridLayout(self)
        self.setStyleSheet("""
            QLabel {
                color : white;
                font-size : 12px;
            }
        """)
        layout.addWidget(QLabel("DHP (cm)"), 1, 0) # DHP moyen
        layout.addWidget(QLabel("ST (m²)"), 2, 0) # Surface terrière
        layout.addWidget(QLabel("Vol (m³)"), 3, 0) # Volume

        layout.addWidget(QLabel("S"), 0, 1, Qt.AlignmentFlag.AlignCenter) # Sélectionné
        layout.addWidget(QLabel("R"), 0, 2, Qt.AlignmentFlag.AlignCenter) # Restant
        layout.addWidget(QLabel("M"), 0, 3, Qt.AlignmentFlag.AlignCenter) # Marchand total
        layout.addWidget(QLabel("%"), 0, 4, Qt.AlignmentFlag.AlignCenter) # Ratio sélectionné / marchand

        for i, key in enumerate(["dbh", "surface", "volume"], start=1):
            if key == "dbh":
                layout.addWidget(QLabel(f"{self.data[key]['merch_mean'] * 100:.2f}"), i, 3)
                continue
            layout.addWidget(QLabel(f"{self.data[key]['selected']:.2f}"), i, 1, Qt.AlignmentFlag.AlignRight)
            layout.addWidget(QLabel(f"{self.data[key]['merchantable'] - self.data[key]['selected']:.2f}"), i, 2, Qt.AlignmentFlag.AlignRight)
            layout.addWidget(QLabel(f"{self.data[key]['merchantable']:.2f}"), i, 3, Qt.AlignmentFlag.AlignRight)
            layout.addWidget(QLabel(f"{self.data[key]['ratio'] * 100:.2f}"), i, 4, Qt.AlignmentFlag.AlignRight)

            if not self.col_dict[key]['col']:
                for j in range(5):
                    layout.itemAtPosition(i, j).widget().setVisible(False)

    @classmethod
    def from_form(cls, propriety_widget: ProprietyWidget, parent=None) -> TreeMarkerWidget:
        """Création d'instance via un formulaire
        
        Paramètres
        propriety_widget : ProprietyWidget transmis à l'instance
        parent : QObject parent
        """
        form = SurfaceColumnForm(propriety_widget._fields)
        if form.exec() != QDialog.DialogCode.Accepted:
            return None

        col_dict = form.get_choices()

        return cls(propriety_widget, col_dict, parent)

    def on_selection_change(self, payload:tuple, marked:bool) -> None:
        """Calcul et met à jour les valeurs des paramètres suite à une modification de sélection
        
        Paramètres
        payload tuple(int, dict) : contient le numéro de ligne et le dictionaire des données de l'arbre sélectionné
        marked bool : est-ce que l'arbre a été sélectionné ou désélectionné
        """
        self._counter += 1
        if self._counter % 25 == 0:
            self._update_selection()
            return

        _, data = payload
        surface = (
            float(data[self.col_dict["surface"]["col"]])
            if self.is_float(data[self.col_dict["surface"]["col"]])
            else 0
        )
        if self.col_dict["volume"]["col"] in payload:
            volume = (
                float(data[self.col_dict["volume"]["col"]])
                if self.is_float(data[self.col_dict["volume"]["col"]])
                else 0
            )
        else:
            volume = 0

        if marked:
            self.data["surface"]["selected"] += surface
            self.data["volume"]["selected"] += volume
        else:
            self.data["surface"]["selected"] -= surface
            self.data["volume"]["selected"] -= volume

        self._update_ratios()
        self._update_display()

    def update_data(self): # TODO : Devrait être appelée lors de la modification des valeurs dans la table
        """Mise à jour des données internes"""
        self._update_sums()
        self._update_dbh_mean()
        self._update_ratios()

    def _update_sums(self):
        """Recalcule des sommes pour n, dbh, surface et volume"""
        for key in self.data.keys():
            if not isinstance(self.data[key], dict):
                continue
            self.data[key]["total"] = 0
            self.data[key]["merchantable"] = 0

        for row in range(self.table.rowCount()):

            dbh = (
                self._get_table_value(row, self.col_dict["dbh"]["col"])
                / self.col_dict["dbh"]["conversion"]
            )
            merchantable = (dbh) >= MERCHANTABLE_DBH_LIM

            surface = (
                self._get_table_value(row, self.col_dict["surface"]["col"])
                / self.col_dict["surface"]["conversion"]
            )

            volume = (
                self._get_table_value(row, self.col_dict["volume"]["col"])
                / self.col_dict["volume"]["conversion"]
            )

            self.data["n"]["total"] += 1
            self.data["dbh"]["total"] += dbh
            self.data["surface"]["total"] += surface
            self.data["volume"]["total"] += volume

            if merchantable:
                self.data["n"]["merchantable"] += 1
                self.data["dbh"]["merchantable"] += dbh
                self.data["surface"]["merchantable"] += surface
                self.data["volume"]["merchantable"] += volume

    def _update_ratios(self):
        """Recalcule des ratios pour surface et volume"""
        for key in ('surface', 'volume'):
            self.data[key]["ratio"] = (
                self.data[key]["selected"] / (self.data[key]["merchantable"] + 1e-10)
            )

    def _update_dbh_mean(self):
        """Recalcule les moyennes de DHP"""
        self.data["dbh"]["mean"] = self.data["dbh"]["total"] / (self.data["n"]["total"] + 1e-10)
        self.data["dbh"]["merch_mean"] = (
            self.data["dbh"]["merchantable"] / (self.data["n"]["merchantable"] + 1e-10)
        )

    def _update_selection(self):
        """Met à jour les données de sélection en revérifiant toute la table"""
        select_col = self.propriety_widget.get_col_from_header("Martelage")
        selection = [
            self.table.item(row, select_col).checkState() == Qt.CheckState.Checked
            for row in range(self.table.rowCount())
        ]

        for field in ["surface", "volume"]:
            col = self.propriety_widget.get_col_from_header(self.col_dict[field]["col"])
            if not col:
                continue

            texts = [
                self.table.item(row, col).text()
                for row in range(self.table.rowCount())
                if self.table.item(row, col) is not None
            ]
            self.data[field]["selected"] = (
                sum(
                    [
                        float(text)
                        for text, selected in zip(texts, selection)
                        if self.is_float(text) and selected
                    ]
                )
                / self.col_dict[field]["conversion"]
            )

    def _update_display(self):
        """Met à jour la donnée dans la mise en page du widget"""
        layout = self.layout()
        for i, key in enumerate(["dbh", "surface", "volume"], start=1):
            if key == "dbh":
                layout.itemAtPosition(i, 3).widget().setText(f"{self.data[key]['merch_mean'] * 100:.2f}")
                continue
            layout.itemAtPosition(i, 1).widget().setText(f"{self.data[key]['selected']:.2f}")
            layout.itemAtPosition(i, 2).widget().setText(f"{self.data[key]['merchantable'] - self.data[key]['selected']:.2f}")
            layout.itemAtPosition(i, 3).widget().setText(f"{self.data[key]['merchantable']:.2f}")
            layout.itemAtPosition(i, 4).widget().setText(f"{self.data[key]['ratio'] * 100:.2f}")
        self.adjustSize()

    def _get_table_value(
        self, row, col
    ):  # NOTE : pourrait être déplacé dans ProprietyWidget
        col = (
            col
            if isinstance(col, int)
            else self.propriety_widget.get_col_from_header(col)
        )
        if not col:
            return 0
        text = self.table.item(row, col).text()
        value = float(text) if self.is_float(text) else 0
        return value

    @staticmethod
    def is_float(value):
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def calculate_surface(dbh: float | int | str, unit: str) -> float | None:
        """Renvoie la surface terrière d'un arbre en mètres carrés"""
        assert unit in CONVERSION_FACTORS, "Unité non reconnue"
        if TreeMarkerWidget.is_float(dbh):
            surf = (float(dbh) / CONVERSION_FACTORS[unit]) ** 2 * 3.1416 / 4
            return surf
        return

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(100, 100, 100, 150))
        painter.drawRoundedRect(self.rect(), 8, 8)
        return super().paintEvent(event)


class ExtendedMarkingStatsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
