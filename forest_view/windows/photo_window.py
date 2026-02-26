from PyQt6.QtCore import Qt, QMarginsF
from PyQt6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QCheckBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from forest_view.widgets import GLWidget, CustomMapWidget, ProprietyWidget

# Panneaux latéral (carte) et inférieur (propriétés).
SIDE_PANEL_WIDTH = 340
TOGGLE_STRIP_WIDTH = 28
BOTTOM_PANEL_HEIGHT = 180
TOGGLE_STRIP_HEIGHT = 28


class PhotoWindow(QMainWindow):
    """Fenêtre principale de l'outil de navigation (panorama + carte + propriétés)."""

    def __init__(self, photo_info, tree_info, photo_dir):
        super().__init__()
        self.setWindowTitle("UdeS Forest View")
        self.setGeometry(300, 300, 800, 600)
        self.on_change_site_requested = None  # callback set by AppManager

        self.gl_widget = GLWidget(self, photo_dir)

        self.map_widget = CustomMapWidget(photo_info, tree_info)
        if tree_info is None:
            self.propriety_widget = ProprietyWidget([])
        else:
            self.propriety_widget = ProprietyWidget(
                [k for k in tree_info[0].keys() if k not in {'x', 'y', 'z'}]
            )
        self.tree_focus_box = QCheckBox('Verouiller la vue à l\'arbre', self)

        self.change_button = QPushButton('Changer de site', self)
        self.change_button.setMinimumHeight(40)
        self.change_button.clicked.connect(self._on_change_site_clicked)

        propriety_box = QGroupBox('Propriétés')
        propriety_box_layout = QVBoxLayout()
        propriety_box_layout.setContentsMargins(1, 0, 1, 1)
        propriety_box_layout.setSpacing(0)
        propriety_box_layout.addWidget(self.propriety_widget, 2)
        propriety_box_layout.addWidget(self.tree_focus_box)
        propriety_box.setLayout(propriety_box_layout)

        self.bottom_panel = QWidget()
        self.bottom_panel.setFixedHeight(BOTTOM_PANEL_HEIGHT)
        bottom_panel_layout = QVBoxLayout(self.bottom_panel)
        bottom_panel_layout.setContentsMargins(0, 0, 0, 0)
        bottom_panel_layout.addWidget(propriety_box)
        self.bottom_panel.setVisible(False)

        self.toggle_bottom_btn = QPushButton("\u25b2", self)
        self.toggle_bottom_btn.setFixedHeight(TOGGLE_STRIP_HEIGHT)
        self.toggle_bottom_btn.setToolTip("Ouvrir les propriétés")
        self.toggle_bottom_btn.clicked.connect(self._toggle_bottom_panel)

        bottom_container = QWidget()
        bottom_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)
        bottom_layout.addWidget(self.bottom_panel, 0)
        bottom_layout.addWidget(self.toggle_bottom_btn, 0)

        self.side_panel = QWidget()
        self.side_panel.setFixedWidth(SIDE_PANEL_WIDTH)
        side_layout = QVBoxLayout(self.side_panel)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.addWidget(self.map_widget, 3)
        side_layout.addWidget(self.change_button, 0)
        self.side_panel.setVisible(False)

        self.toggle_panel_btn = QPushButton("\u25c0", self)
        self.toggle_panel_btn.setFixedSize(TOGGLE_STRIP_WIDTH, 80)
        self.toggle_panel_btn.setToolTip("Ouvrir la carte")
        self.toggle_panel_btn.clicked.connect(self._toggle_side_panel)

        right_container = QWidget()
        right_container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        right_layout = QHBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self.side_panel, 0)
        right_layout.addWidget(self.toggle_panel_btn, 0)

        content_row = QWidget()
        content_row_layout = QHBoxLayout(content_row)
        content_row_layout.setContentsMargins(0, 0, 0, 0)
        content_row_layout.addWidget(self.gl_widget, 3)
        content_row_layout.addWidget(right_container, 0)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(content_row, 3)
        main_layout.addWidget(bottom_container, 0)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def _toggle_side_panel(self):
        visible = self.side_panel.isVisible()
        self.side_panel.setVisible(not visible)
        if visible:
            self.toggle_panel_btn.setText("\u25c0")
            self.toggle_panel_btn.setToolTip("Ouvrir la carte")
        else:
            self.toggle_panel_btn.setText("\u25b6")
            self.toggle_panel_btn.setToolTip("Fermer la carte")

    def _toggle_bottom_panel(self):
        visible = self.bottom_panel.isVisible()
        self.bottom_panel.setVisible(not visible)
        if visible:
            self.toggle_bottom_btn.setText("\u25b2")
            self.toggle_bottom_btn.setToolTip("Ouvrir les propriétés")
        else:
            self.toggle_bottom_btn.setText("\u25bc")
            self.toggle_bottom_btn.setToolTip("Fermer les propriétés")

    def _on_change_site_clicked(self):
        if callable(self.on_change_site_requested):
            self.on_change_site_requested()

    def change_site(self, photo_info, tree_info, photo_dir):
        """Réinitialise la fenêtre pour un nouveau site (données + carte + propriétés + panorama)."""
        self.gl_widget.new_pointer_direction.disconnect()
        self.map_widget.reset()
        self.gl_widget.new_pointer_direction.connect(self.map_widget.pointer.rotate_pointer)

        if photo_info is not None:
            self.map_widget.plot_photo_coordinates(photo_info)
        if tree_info is not None:
            self.map_widget.plot_tree_coordinates(tree_info)
        if photo_info:
            self.map_widget.pointer.setPos(float(photo_info[0]['x']), -float(photo_info[0]['y']))

        self.map_widget.fitInView(self.map_widget.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.map_widget.scene.setSceneRect(
            self.map_widget.scene.itemsBoundingRect().marginsAdded(QMarginsF(10, 10, 10, 10))
        )

        self.propriety_widget.reset()
        if tree_info is None:
            self.propriety_widget.set_fields([])
        else:
            self.propriety_widget.set_fields(
                [k for k in tree_info[0].keys() if k not in {'x', 'y', 'z'}]
            )

        self.gl_widget.reset()
        self.gl_widget.photo_dir = photo_dir

    def closeEvent(self, event):
        super().closeEvent(event)
        if not getattr(self, '_returning_to_project_selection', False):
            QApplication.quit()
