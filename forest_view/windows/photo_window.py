from PyQt6.QtCore import Qt, QMarginsF
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from forest_view.widgets import GLWidget, CustomMapWidget, ProprietyWidget


def _empty_photo_placeholder():
    """Widget affiché dans la zone photo lorsqu'aucune image n'est sélectionnée."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    label = QLabel(
        "Sélectionnez une photo sur la carte pour commencer à visualiser les panoramas."
    )
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setWordWrap(True)
    font = QFont()
    font.setPointSize(12)
    label.setFont(font)
    label.setStyleSheet("color: #555;")
    layout.addWidget(label, 0, Qt.AlignmentFlag.AlignCenter)
    widget.setStyleSheet("background-color: #e8e8e8;")
    return widget


class PhotoWindow(QMainWindow):
    def __init__(self, photo_info, tree_info, photo_dir):
        super().__init__()
        self.setWindowTitle("UdeS Forest View")
        self.setGeometry(300, 300, 800, 600)

        self.gl_widget = GLWidget(self, photo_dir)
        self._photo_stack = QStackedLayout()
        self._photo_stack.addWidget(self.gl_widget)
        self._photo_stack.addWidget(_empty_photo_placeholder())
        self._photo_stack.setCurrentIndex(1)
        photo_container = QWidget()
        photo_container.setLayout(self._photo_stack)

        self.map_widget = CustomMapWidget(photo_info, tree_info)
        self.map_widget.new_panorama.connect(self._on_panorama_selected)
        if tree_info is None:
            self.propriety_widget = ProprietyWidget([])
        else:
            self.propriety_widget = ProprietyWidget(
                [k for k in tree_info[0].keys() if k not in {'x', 'y', 'z'}]
            )
        self.change_button = QPushButton('Changer de site')

        propriety_box = QGroupBox('Propriétés')
        propriety_box_layout = QVBoxLayout()
        propriety_box_layout.setContentsMargins(1, 0, 1, 1)
        propriety_box_layout.setSpacing(0)
        propriety_box_layout.addWidget(self.propriety_widget)
        propriety_box.setLayout(propriety_box_layout)

        right_layout = QVBoxLayout()
        right_layout.addWidget(propriety_box, 2)
        right_layout.addWidget(self.map_widget, 3)
        right_layout.addWidget(self.change_button)

        main_layout = QHBoxLayout()
        main_layout.addWidget(photo_container, 3)
        main_layout.addLayout(right_layout, 1)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def _on_panorama_selected(self, image_path, image_yaw, image_pitch, image_roll):
        if image_path:
            self._photo_stack.setCurrentIndex(0)

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
        self._photo_stack.setCurrentIndex(1)

    def closeEvent(self, event):
        super().closeEvent(event)
        QApplication.quit()
