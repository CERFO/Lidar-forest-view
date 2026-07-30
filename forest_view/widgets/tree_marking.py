from itertools import product

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QGridLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,  
)

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
        {"dbh" : {"col": , "units":},
        "surface" : {"col": , "units":},
        "volume" : {"col": , "units":},}
    """

    tree_selection_changed = pyqtSignal()

    def __init__(self, propriety_widget: ProprietyWidget, col_dict: dict, parent=None):
        super().__init__(parent)

        self.propriety_widget = propriety_widget
        self.table = propriety_widget.table
        self._counter = 0
        self.col_dict = col_dict
        self.extended_widget = None

        self.data = dict.fromkeys(col_dict.keys()) # TODO : revoir la construction pour ne prendre que les variables à suivre
        for key in self.data.keys():
            self.data[key] = {"selected": 0, "merchantable": 0, "total": 0, "ratio": 0}
        self.data.update({"n": {"merchantable": 0, "total": 0},
                          "area_ha": 1})  # TODO : trouver comment calculer la surface de la placette

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
                    surf_item.setText(f"{surf:.4f}")
            self.col_dict["surface"]["conversion"] = 1

        self.update_data()
        self.propriety_widget.add_selection_col("Martelage")
        self._build_layout()

    def _build_layout(self):
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

        self.extension_btn = QPushButton("⇱", self)
        self.extension_btn.setStyleSheet("""
            QPushButton {
                padding: 0px;
            }
        """)
        self.extension_btn.setFixedSize(21,21)
        self.extension_btn.clicked.connect(self.toggle_extended_widget)
        layout.addWidget(self.extension_btn, 0, 0)

        for i, key in enumerate(["dbh", "surface", "volume"], start=1):
            if key == "dbh":
                layout.addWidget(QLabel(f"{self.data[key]["merch_mean"] * 100:.2f}"), i, 3)
                continue
            layout.addWidget(QLabel(f"{self.data[key]["selected"]:.2f}"), i, 1, Qt.AlignmentFlag.AlignRight)
            layout.addWidget(QLabel(f"{self.data[key]["merchantable"] - self.data[key]["selected"]:.2f}"), i, 2, Qt.AlignmentFlag.AlignRight)
            layout.addWidget(QLabel(f"{self.data[key]["merchantable"]:.2f}"), i, 3, Qt.AlignmentFlag.AlignRight)
            layout.addWidget(QLabel(f"{self.data[key]["ratio"] * 100:.2f}"), i, 4, Qt.AlignmentFlag.AlignRight)

            if not self.col_dict[key]["col"]:
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

        if self.extended_widget:
            self.extended_widget.update_data()
            self.extended_widget.update_display()

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
                self.propriety_widget.get_float(row, self.col_dict["dbh"]["col"], 0)
                / self.col_dict["dbh"]["conversion"]
            )
            merchantable = (dbh) >= MERCHANTABLE_DBH_LIM

            surface = (
                self.propriety_widget.get_float(row, self.col_dict["surface"]["col"], 0)
                / self.col_dict["surface"]["conversion"]
            )

            volume = (
                self.propriety_widget.get_float(row, self.col_dict["volume"]["col"], 0)
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
        for key in ("surface", "volume"):
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
                layout.itemAtPosition(i, 3).widget().setText(f"{self.data[key]["merch_mean"] * 100:.2f}")
                continue
            layout.itemAtPosition(i, 1).widget().setText(f"{self.data[key]["selected"]:.2f}")
            layout.itemAtPosition(i, 2).widget().setText(f"{self.data[key]["merchantable"] - self.data[key]["selected"]:.2f}")
            layout.itemAtPosition(i, 3).widget().setText(f"{self.data[key]["merchantable"]:.2f}")
            layout.itemAtPosition(i, 4).widget().setText(f"{self.data[key]["ratio"] * 100:.2f}")
        self.adjustSize()

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
    
    def toggle_extended_widget(self):
        if not self.extended_widget:
            self.extended_widget = ExtendedMarkingStatsWidget(self.propriety_widget, self.col_dict, area=self.data["area_ha"], parent=self)
        
        if self.extended_widget.isVisible():
            self.extended_widget.hide()
            self.extension_btn.setText("⇱")
        else:
            self.extended_widget.show()
            self.extension_btn.setText("⇲")

    def remove_extended_widget(self):
        if not self.extended_widget:
            return

        self.extended_widget.close()
        self.extended_widget = None
        self.extension_btn.setText("⇱")


class ExtendedMarkingStatsWidget(QWidget):
    """Widget étendu avec statistiques ventilées par classe"""
    def __init__(self, propriety_widget: ProprietyWidget, col_dict: dict, area=1, parent=None):
        super().__init__(parent)

        self.setWindowFlag(Qt.Window, True)
        self.setMinimumWidth(200)

        self.col_dict = col_dict
        if not self.col_dict.get("classes", {}).get("col"):
            self.col_dict.update({"classes": {"col": None}})
        self.propriety_widget = propriety_widget
        self.table = propriety_widget.table
        self.area_ha = area

        self.var = ["n", "surface", "volume"]
        self.cls = self._get_classes(self.col_dict["classes"]["col"])
        self.select_type = ["selected", "remaining"]
        self.merch_type = ["merchantable", "total"]
        self.normalization = ["none", "per_ha"]
        self.keys = list(product(self.var, self.cls, self.select_type, self.merch_type, self.normalization))

        self.data = {}
        for key in self.keys:
            self.data[key] = 0

        self.update_data()
        self._build_layout()

    def _get_classes(self, col_name):
        if col_name:
            col = self.propriety_widget.get_col_from_header(col_name)
            if col is None:
                return ["total"]
            cls = list(set([
                self.table.item(row, col).text()
                for row in range(self.table.rowCount())
                if self.table.item(row, col) is not None
            ]))
            cls = self.sort_classes(cls) + ["total"]
        else:
            cls = ["total"]
        return cls

    def update_data(self):
        self._update_sums()
        self._update_normalization()

    def _update_sums(self):
        for key in self.keys:
            if "none" not in key:
                continue
            self.data[key] = 0

        select_col = self.propriety_widget.get_col_from_header("Martelage")
        dbh_col = self.propriety_widget.get_col_from_header(self.col_dict["dbh"]["col"])
        class_col = self.propriety_widget.get_col_from_header(self.col_dict["classes"]["col"])
        var_cols = [self.propriety_widget.get_col_from_header(self.col_dict.get(var, {}).get("col")) for var in self.var]
        
        for row in range(self.table.rowCount()):
            merchantable = (
                self.propriety_widget.get_float(row, dbh_col, 0)
                / self.col_dict["dbh"]["conversion"]
                >= MERCHANTABLE_DBH_LIM
                )
            selected = self.table.item(row, select_col).checkState() == Qt.CheckState.Checked
            cls = self.table.item(row, class_col).text() if class_col is not None else ""

            for var, col in zip(self.var, var_cols):
                if var == "n":
                    value = 1
                elif self.col_dict[var].get("conversion"):
                    value = self.propriety_widget.get_float(row, col, 0) / self.col_dict[var].get("conversion")
                else:
                    value = self.propriety_widget.get_float(row, col, 0)

                if cls not in self.cls:
                    if selected:
                        self.data[(var, "total", "selected", "total", "none")] += value
                    else:
                        self.data[(var, "total", "remaining", "total", "none")] += value

                    if merchantable:
                        if selected:
                            self.data[(var, "total", "selected", "merchantable", "none")] += value
                        else:
                            self.data[(var, "total", "remaining", "merchantable", "none")] += value
                    continue

                if selected:
                    self.data[(var, cls, "selected", "total", "none")] += value
                    self.data[(var, "total", "selected", "total", "none")] += value
                else:
                    self.data[(var, cls, "remaining", "total", "none")] += value
                    self.data[(var, "total", "remaining", "total", "none")] += value

                if merchantable:
                    if selected:
                        self.data[(var, cls, "selected", "merchantable", "none")] += value
                        self.data[(var, "total", "selected", "merchantable", "none")] += value
                    else:
                        self.data[(var, cls, "remaining", "merchantable", "none")] += value
                        self.data[(var, "total", "remaining", "merchantable", "none")] += value

    def _update_normalization(self):
        for key in self.keys:
            if "per_ha" not in key:
                continue
            self.data[key] = 0

        for key in product(self.var, self.cls, self.select_type, self.merch_type):
            self.data[key + tuple(["per_ha"])] = self.data[key + tuple(["none"])] / self.area_ha

    def _update_break_down(self):
        class_col_name, accepted = QInputDialog.getItem(self, "Classes", "Colonne de classes", self.propriety_widget._fields + ["Aucune"])
        if not accepted:
            return
        class_col_name = None if class_col_name == "Aucune" else class_col_name
        self.col_dict["classes"]["col"] = class_col_name
        self.cls = self._get_classes(class_col_name)

        self.keys = list(product(self.var, self.cls, self.select_type, self.merch_type, self.normalization))
        self.data = {}
        for key in self.keys:
            self.data[key] = 0
        self.update_data()

        self._clear_grid_layout(self.selected_layout)
        self._clear_grid_layout(self.remaining_layout)

        self._fill_grid_layout(self.selected_layout, 'selected')
        self._fill_grid_layout(self.remaining_layout, "remaining")

        QApplication.processEvents() # Permet la délétion des anciens widgets
        self.adjustSize()
    
    @staticmethod
    def sort_classes(classes: set[str]):
        """Ordonne les classes en entrée si elles sont d'un type connue, sinon fait un sort sandard"""
        classes = set(classes)
        
        if all([cls in classes for cls in ["M", "S", "C", "R"]]):
            main_classes = ["M", "S", "C", "R"]
            other = list(classes.difference(set(main_classes)))
        elif all([cls in classes for cls in ["A", "B", "C", "D"]]):
            main_classes = ["A", "B", "C", "D"]
            other = list(classes.difference(set(main_classes)))
        else:
            if "" in classes:
                other = [""]
                classes.remove("")
            else:
                other = []
            main_classes = sorted(classes)
            
        main_classes.extend(other)
        return main_classes

    @staticmethod
    def is_float(value):
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
        
    def _build_layout(self):
        self.setStyleSheet("""
            QLabel {
                color : black;
                font-size : 12px;
            }
        """)
        
        global_layout = QVBoxLayout(self)

        global_layout.addWidget(QLabel("Sélectionnée", self), alignment=Qt.AlignmentFlag.AlignCenter)
        self.selected_layout = QGridLayout()
        self._fill_grid_layout(self.selected_layout, "selected")
        global_layout.addLayout(self.selected_layout)

        global_layout.addWidget(QLabel("Restant", self), alignment=Qt.AlignmentFlag.AlignCenter)
        self.remaining_layout = QGridLayout()
        self._fill_grid_layout(self.remaining_layout, "remaining")
        global_layout.addLayout(self.remaining_layout)

        ventilate_btn = QPushButton("Ventiler", self)
        ventilate_btn.clicked.connect(self._update_break_down)
        global_layout.addWidget(ventilate_btn)

    def _clear_grid_layout(self, layout):
        for row in range(layout.rowCount()):
            for col in range(layout.columnCount()):
                if layout.itemAtPosition(row, col):
                    layout.itemAtPosition(row, col).widget().deleteLater()

    def _fill_grid_layout(self, layout, selection_type):
        var_names = {
            ("n", "merchantable") : "NM",
            ("n", "total") : "NT",
            ("surface", "merchantable") : "GM",
            ("surface", "total") : "GT",
            ("volume", "merchantable") : "VM",
            ("volume", "total") : "VT",
        }

        for row, var_type in enumerate(product(self.var, self.merch_type), start=1):
            for col, cls in enumerate(self.cls, start=1):
                if row == 1:
                    layout.addWidget(QLabel(cls if cls else "Autre", self), 0, col, alignment=Qt.AlignmentFlag.AlignCenter)
                if col == 1:
                    layout.addWidget(QLabel(var_names[var_type], self), row, 0)

                key = (var_type[0], cls, selection_type, var_type[1], "per_ha")
                fmt = ".0f" if "n" in key else ".2f"
                layout.addWidget(QLabel(f"{self.data[key]:{fmt}}", self), row, col, alignment=Qt.AlignmentFlag.AlignCenter)


    def update_display(self):
        for row, var_type in enumerate(product(self.var, self.merch_type), start=1):
            for col, cls in enumerate(self.cls, start=1):
                key = (var_type[0], cls, "selected", var_type[1], "per_ha")
                fmt = ".0f" if "n" in key else ".2f"
                self.selected_layout.itemAtPosition(row, col).widget().setText(f"{self.data[key]:{fmt}}")

        for row, var_type in enumerate(product(self.var, self.merch_type), start=1):
            for col, cls in enumerate(self.cls, start=1):
                key = (var_type[0], cls, "remaining", var_type[1], "per_ha")
                fmt = ".0f" if "n" in key else ".2f"
                self.remaining_layout.itemAtPosition(row, col).widget().setText(f"{self.data[key]:{fmt}}")

    def closeEvent(self, a0):
        if hasattr(self.parent(), "remove_extended_widget"):
            self.parent().remove_extended_widget()
        self.deleteLater()
        return super().closeEvent(a0)
