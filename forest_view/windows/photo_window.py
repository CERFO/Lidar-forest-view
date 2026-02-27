from PyQt6.QtCore import Qt, QMarginsF, QRect, QSize
from PyQt6.QtGui import QIcon, QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QCheckBox,
    QSizePolicy,
    QStyle,
    QStyleOptionButton,
    QVBoxLayout,
    QWidget,
)

from forest_view.widgets import GLWidget, CustomMapWidget, ProprietyWidget

SIDE_PANEL_WIDTH = 340
TOGGLE_STRIP_WIDTH = 28
TOGGLE_MAP_BTN_WIDTH = 28
BOTTOM_PANEL_HEIGHT = 180
TOGGLE_STRIP_HEIGHT = 28
TOGGLE_TABLE_BTN_MIN_WIDTH = 140


class VerticalLabelPushButton(QPushButton):
    """Bouton qui affiche son label en vertical (haut vers bas) pour rester étroit."""
    def paintEvent(self, event):
        option = QStyleOptionButton()
        self.initStyleOption(option)
        option.text = ""
        option.icon = QIcon()
        painter = QPainter(self)
        self.style().drawControl(QStyle.ControlElement.CE_PushButton, option, painter, self)
        margin = 4
        icon_bottom = margin
        icon = self.icon()
        if not icon.isNull():
            icon_size = self.iconSize()
            if not icon_size.isValid():
                icon_size = QSize(20, 20)
            icon_rect = QRect(margin, margin, self.width() - 2 * margin, icon_size.height())
            painter.save()
            painter.translate(icon_rect.x() + icon_rect.width(), icon_rect.y())
            painter.scale(-1, 1)
            painter.translate(-icon_rect.width(), 0)
            icon.paint(painter, QRect(0, 0, icon_rect.width(), icon_rect.height()), Qt.AlignmentFlag.AlignCenter)
            painter.restore()
            icon_bottom = margin + icon_size.height()
        text = self.text()
        if text:
            painter.save()
            font = self.font()
            painter.setFont(font)
            fm = painter.fontMetrics()
            text_width = fm.horizontalAdvance(text)
            font_height = fm.height()
            center_x = self.width() // 2
            center_y = self.height() // 2
            painter.translate(center_x, center_y)
            painter.rotate(90)
            text_rect = QRect(-text_width // 2, -font_height // 2, text_width, font_height)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)
            painter.restore()


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

        self.filter_selected_only_cb = QCheckBox("Afficher uniquement la ligne sélectionnée", self)
        self.filter_selected_only_cb.setChecked(False)
        self.filter_selected_only_cb.toggled.connect(self.propriety_widget.set_filter_only_selected)
        bottom_options = QWidget()
        propriety_box = QGroupBox('Propriétés')
        propriety_box_layout = QVBoxLayout()
        propriety_box_layout.setContentsMargins(1, 0, 1, 1)
        propriety_box_layout.setSpacing(0)
        propriety_box_layout.addWidget(self.propriety_widget, 2)
        propriety_box_layout.addWidget(bottom_options)
        propriety_box.setLayout(propriety_box_layout)

        self.bottom_panel = QWidget()
        self.bottom_panel.setFixedHeight(BOTTOM_PANEL_HEIGHT)
        bottom_panel_layout = QVBoxLayout(self.bottom_panel)
        bottom_panel_layout.setContentsMargins(0, 0, 0, 0)
        bottom_panel_layout.addWidget(propriety_box)
        self.bottom_panel.setVisible(False)

        self.toggle_bottom_btn = QPushButton(self)
        self.toggle_bottom_btn.setFixedHeight(TOGGLE_STRIP_HEIGHT)
        self.toggle_bottom_btn.setMinimumWidth(TOGGLE_TABLE_BTN_MIN_WIDTH)
        self._set_table_button_icon_and_text(open_=False)
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
        side_layout.addWidget(self.map_widget, 1)
        self.side_panel.setVisible(False)

        self.toggle_panel_btn = VerticalLabelPushButton(self)
        self.toggle_panel_btn.setFixedSize(TOGGLE_MAP_BTN_WIDTH, 80)
        self.toggle_panel_btn.setIconSize(QSize(20, 20))
        self._set_map_button_icon_and_text(open_=False)
        self.toggle_panel_btn.clicked.connect(self._toggle_side_panel)

        right_buttons = QWidget()
        right_buttons_layout = QVBoxLayout(right_buttons)
        right_buttons_layout.setContentsMargins(0, 0, 0, 0)
        right_buttons_layout.addWidget(self.toggle_panel_btn, 0)
        right_buttons_layout.addStretch(1)

        right_container = QWidget()
        right_container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        right_layout = QHBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.side_panel, 0)
        right_layout.addWidget(right_buttons, 0)

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

    def _map_icon(self):
        for name in ("view-map", "map", "map-marked", "mark-location", "place", "globe", "world"):
            icon = QIcon.fromTheme(name)
            if not icon.isNull():
                return icon
        return QIcon()

    def _table_icon(self):
        icon = QIcon.fromTheme("view-table")
        if icon.isNull():
            icon = QIcon.fromTheme("x-office-spreadsheet")
        if icon.isNull():
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView)
        return icon

    def _set_map_button_icon_and_text(self, open_):
        self.toggle_panel_btn.setIcon(self._map_icon())
        self.toggle_panel_btn.setText("Carte")
        if open_:
            self.toggle_panel_btn.setToolTip("Fermer la carte")
        else:
            self.toggle_panel_btn.setToolTip("Ouvrir la carte")

    def _set_table_button_icon_and_text(self, open_):
        self.toggle_bottom_btn.setIcon(self._table_icon())
        if open_:
            self.toggle_bottom_btn.setText("Table d'attributs")
            self.toggle_bottom_btn.setToolTip("Fermer la table d'attributs")
        else:
            self.toggle_bottom_btn.setText("Table d'attributs")
            self.toggle_bottom_btn.setToolTip("Ouvrir la table d'attributs")

    def _toggle_side_panel(self):
        visible = self.side_panel.isVisible()
        self.side_panel.setVisible(not visible)
        self._set_map_button_icon_and_text(open_=not visible)

    def _toggle_bottom_panel(self):
        visible = self.bottom_panel.isVisible()
        self.bottom_panel.setVisible(not visible)
        self._set_table_button_icon_and_text(open_=not visible)

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
