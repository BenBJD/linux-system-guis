"""Desktop styling, theme definitions, and UX protections for Linux System GUIs."""

import os
import re
from PyQt6.QtCore import QEvent, QObject
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QTabBar,
    QTableWidget,
    QTabWidget,
    QToolButton,
)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
DOWN_ARROW_PATH = os.path.join(ASSETS_DIR, "down_arrow.svg").replace("\\", "/")
UP_ARROW_PATH = os.path.join(ASSETS_DIR, "up_arrow.svg").replace("\\", "/")


def _esc_amp(val):
    if isinstance(val, str):
        return re.sub(r"(?<!&)&(?!&)", "&&", val)
    return val


def _escape_button_ampersands() -> None:
    """Ensures literal '&' in button, checkbox, radio, groupbox, and tab labels renders
    correctly instead of being treated by Qt as a keyboard mnemonic/shortcut character
    (which otherwise hides '&' or renders it as an underline '_').
    """
    for cls in (QPushButton, QToolButton, QCheckBox, QRadioButton):
        if getattr(cls, "_amp_patched", False):
            continue
        orig_init = cls.__init__
        orig_setText = cls.setText

        def _make_init(old_init):
            def patched_init(self, *args, **kwargs):
                new_args = list(args)
                if len(new_args) >= 1 and isinstance(new_args[0], str):
                    new_args[0] = _esc_amp(new_args[0])
                elif len(new_args) >= 2 and isinstance(new_args[1], str):
                    new_args[1] = _esc_amp(new_args[1])
                if "text" in kwargs and isinstance(kwargs["text"], str):
                    kwargs["text"] = _esc_amp(kwargs["text"])
                old_init(self, *new_args, **kwargs)
            return patched_init

        def _make_setText(old_setText):
            def patched_setText(self, text):
                old_setText(self, _esc_amp(text))
            return patched_setText

        cls.__init__ = _make_init(orig_init)
        cls.setText = _make_setText(orig_setText)
        cls._amp_patched = True

    if not getattr(QGroupBox, "_amp_patched", False):
        orig_gb_init = QGroupBox.__init__
        orig_gb_setTitle = QGroupBox.setTitle

        def _gb_init(self, *args, **kwargs):
            new_args = list(args)
            if len(new_args) >= 1 and isinstance(new_args[0], str):
                new_args[0] = _esc_amp(new_args[0])
            if "title" in kwargs and isinstance(kwargs["title"], str):
                kwargs["title"] = _esc_amp(kwargs["title"])
            orig_gb_init(self, *new_args, **kwargs)

        def _gb_setTitle(self, title):
            orig_gb_setTitle(self, _esc_amp(title))

        QGroupBox.__init__ = _gb_init
        QGroupBox.setTitle = _gb_setTitle
        QGroupBox._amp_patched = True

    if not getattr(QTabWidget, "_amp_patched", False):
        orig_tw_addTab = QTabWidget.addTab
        orig_tw_insertTab = QTabWidget.insertTab
        orig_tw_setTabText = QTabWidget.setTabText

        def _tw_addTab(self, *args):
            new_args = [_esc_amp(a) if isinstance(a, str) else a for a in args]
            return orig_tw_addTab(self, *new_args)

        def _tw_insertTab(self, *args):
            new_args = [_esc_amp(a) if isinstance(a, str) else a for a in args]
            return orig_tw_insertTab(self, *new_args)

        def _tw_setTabText(self, index, text):
            return orig_tw_setTabText(self, index, _esc_amp(text))

        QTabWidget.addTab = _tw_addTab
        QTabWidget.insertTab = _tw_insertTab
        QTabWidget.setTabText = _tw_setTabText
        QTabWidget._amp_patched = True

    if not getattr(QTabBar, "_amp_patched", False):
        orig_tb_addTab = QTabBar.addTab
        orig_tb_insertTab = QTabBar.insertTab
        orig_tb_setTabText = QTabBar.setTabText

        def _tb_addTab(self, *args):
            new_args = [_esc_amp(a) if isinstance(a, str) else a for a in args]
            return orig_tb_addTab(self, *new_args)

        def _tb_insertTab(self, *args):
            new_args = [_esc_amp(a) if isinstance(a, str) else a for a in args]
            return orig_tb_insertTab(self, *new_args)

        def _tb_setTabText(self, index, text):
            return orig_tb_setTabText(self, index, _esc_amp(text))

        QTabBar.addTab = _tb_addTab
        QTabBar.insertTab = _tb_insertTab
        QTabBar.setTabText = _tb_setTabText
        QTabBar._amp_patched = True

    if not getattr(QTableWidget, "_readonly_patched", False):
        orig_tbl_init = QTableWidget.__init__

        def _tbl_init(self, *args, **kwargs):
            orig_tbl_init(self, *args, **kwargs)
            self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        QTableWidget.__init__ = _tbl_init
        QTableWidget._readonly_patched = True


# Run immediately on module import so any buttons created before apply_theme are protected
_escape_button_ampersands()


def build_stylesheet() -> str:
    return f"""
QMainWindow, QDialog, QSplitter {{
    background-color: #16181d;
    color: #f0f3f6;
}}

/* Ensure all scroll areas and viewport containers have consistent dark background */
QScrollArea,
QScrollArea > QWidget,
QScrollArea > QWidget > QWidget,
QScrollArea QWidget#qt_scrollarea_viewport {{
    background-color: #16181d;
    border: none;
}}

QWidget {{
    font-family: 'Inter', 'Cantarell', 'Noto Sans', 'Segoe UI', sans-serif;
    font-size: 13px;
    color: #f0f3f6;
}}

QLabel {{
    border: none;
    background: transparent;
}}

/* Card-style GroupBox with refined header */
QGroupBox {{
    font-weight: 600;
    font-size: 13px;
    border: 1px solid #282d38;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 14px;
    padding-bottom: 10px;
    padding-left: 12px;
    padding-right: 12px;
    background-color: #1a1d24;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #85abf2;
    letter-spacing: 0.2px;
}}

/* Standard and Semantic Action Buttons */
QPushButton {{
    background-color: #232731;
    color: #f0f3f6;
    border: 1px solid #333a4a;
    border-radius: 5px;
    padding: 5px 14px;
    font-weight: 500;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: #2d3444;
    border-color: #444e63;
    color: #ffffff;
}}

QPushButton:pressed {{
    background-color: #1c2029;
    border-color: #2a303d;
}}

QPushButton:disabled {{
    background-color: #181a20;
    color: #636a75;
    border-color: #242832;
}}

QPushButton#primaryBtn {{
    background-color: #2360b8;
    color: #ffffff;
    border: 1px solid #3b82f6;
    font-weight: 600;
}}

QPushButton#primaryBtn:hover {{
    background-color: #2e71d4;
    border-color: #60a5fa;
}}

QPushButton#primaryBtn:pressed {{
    background-color: #1a4c96;
}}

QPushButton#primaryBtn:disabled {{
    background-color: #1b3866;
    color: #7997c4;
    border-color: #254b85;
}}

QPushButton#dangerBtn {{
    background-color: #a82835;
    color: #ffffff;
    border: 1px solid #da3633;
    font-weight: 600;
}}

QPushButton#dangerBtn:hover {{
    background-color: #be3240;
    border-color: #f85149;
}}

QPushButton#dangerBtn:pressed {{
    background-color: #8c1f2b;
}}

/* Input Controls with recessed dark wells */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: #121418;
    border: 1px solid #2e3442;
    border-radius: 5px;
    padding: 5px 8px;
    color: #f0f3f6;
    selection-background-color: #244577;
    selection-color: #ffffff;
    font-size: 13px;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid #388bfd;
}}

/* ComboBox with visible drop-down indicator arrow */
QComboBox {{
    background-color: #121418;
    border: 1px solid #2e3442;
    border-radius: 5px;
    padding: 5px 26px 5px 8px;
    color: #f0f3f6;
    selection-background-color: #244577;
    selection-color: #ffffff;
    font-size: 13px;
}}

QComboBox:focus {{
    border: 1px solid #388bfd;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 22px;
    border-left: 1px solid #2e3442;
    border-top-right-radius: 5px;
    border-bottom-right-radius: 5px;
    background-color: #121418;
}}

QComboBox::drop-down:hover {{
    background-color: #222732;
}}

QComboBox::down-arrow {{
    image: url("{DOWN_ARROW_PATH}");
    width: 9px;
    height: 5px;
}}

QComboBox QAbstractItemView {{
    background-color: #16181d;
    border: 1px solid #333a4a;
    border-radius: 5px;
    color: #f0f3f6;
    selection-background-color: #203554;
    selection-color: #ffffff;
    padding: 4px;
    font-size: 13px;
}}

/* SpinBox with up and down buttons and arrows */
QSpinBox, QDoubleSpinBox {{
    background-color: #121418;
    border: 1px solid #2e3442;
    border-radius: 5px;
    padding: 5px 22px 5px 8px;
    color: #f0f3f6;
    selection-background-color: #244577;
    selection-color: #ffffff;
    font-size: 13px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid #388bfd;
}}

QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 18px;
    border-left: 1px solid #2e3442;
    border-bottom: 1px solid #2e3442;
    border-top-right-radius: 4px;
    background-color: #121418;
}}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
    background-color: #222732;
}}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url("{UP_ARROW_PATH}");
    width: 7px;
    height: 4px;
}}

QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 18px;
    border-left: 1px solid #2e3442;
    border-bottom-right-radius: 4px;
    background-color: #121418;
}}

QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: #222732;
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url("{DOWN_ARROW_PATH}");
    width: 7px;
    height: 4px;
}}

QCheckBox, QRadioButton {{
    spacing: 8px;
    color: #f0f3f6;
    background: transparent;
    font-size: 13px;
}}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #444c5e;
    background-color: #121418;
}}

QRadioButton::indicator {{
    border-radius: 8px;
}}

QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: #388bfd;
}}

QCheckBox::indicator:checked {{
    background-color: #2360b8;
    border: 1px solid #3b82f6;
}}

QRadioButton::indicator:checked {{
    background-color: #2360b8;
    border: 2px solid #3b82f6;
}}

/* Polished Tables and Trees */
QTableWidget, QTreeWidget, QListWidget {{
    background-color: #121418;
    border: 1px solid #282d38;
    border-radius: 6px;
    gridline-color: #1c2028;
    color: #f0f3f6;
    selection-background-color: #1d3352;
    selection-color: #ffffff;
    font-size: 13px;
}}

QTableWidget::item, QTreeWidget::item {{
    padding: 5px 8px;
}}

QTableWidget::item:hover, QTreeWidget::item:hover {{
    background-color: #181d26;
}}

QHeaderView::section {{
    background-color: #1a1d24;
    color: #9198a1;
    padding: 7px 10px;
    font-weight: 600;
    font-size: 12px;
    border: none;
    border-bottom: 1px solid #282d38;
    border-right: 1px solid #1f232b;
}}

/* Segmented / Tab Controls */
QTabWidget::pane {{
    border: 1px solid #282d38;
    border-radius: 6px;
    background-color: #1a1d24;
    padding: 10px;
}}

QTabBar::tab {{
    background-color: #131519;
    color: #9198a1;
    padding: 7px 16px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    margin-right: 4px;
    font-size: 13px;
    font-weight: 500;
}}

QTabBar::tab:hover {{
    background-color: #1d212b;
    color: #c9d1d9;
}}

QTabBar::tab:selected {{
    background-color: #242a36;
    color: #ffffff;
    font-weight: 600;
    border-bottom: 2px solid #388bfd;
}}

/* Sleek Minimal Scrollbars */
QScrollBar:vertical {{
    background: #121418;
    width: 8px;
    margin: 0;
    border-radius: 4px;
}}

QScrollBar:horizontal {{
    background: #121418;
    height: 8px;
    margin: 0;
    border-radius: 4px;
}}

QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: #2e3442;
    min-height: 24px;
    min-width: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
    background: #444d61;
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0px;
    height: 0px;
}}

QSplitter::handle {{
    background-color: #282d38;
}}

QToolTip {{
    background-color: #181b22;
    color: #f0f3f6;
    border: 1px solid #3d4352;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 13px;
}}
"""


class NoWheelInputFilter(QObject):
    """Global event filter that prevents mouse wheel events over inputs (QComboBox,
    QSpinBox, QSlider) from accidentally changing their values.
    Instead, forwards the scroll event to the parent container so page scrolling is preserved.
    """

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            if isinstance(obj, (QComboBox, QSpinBox, QDoubleSpinBox, QSlider)):
                event.ignore()
                parent = obj.parentWidget()
                if parent:
                    QApplication.sendEvent(parent, event)
                return True
        return super().eventFilter(obj, event)


def apply_theme(app: QApplication) -> None:
    """Applies clean desktop theme, dark palette, custom assets, and UX protections."""
    # Ensure button ampersand escaping is active
    _escape_button_ampersands()

    # 1. Base palette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#16181d"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#f0f3f6"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#121418"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#181b22"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#f0f3f6"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#232731"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#f0f3f6"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#388bfd"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    # 2. Stylesheet
    app.setStyleSheet(build_stylesheet())

    # 3. Disable mouse scrolling value mutation on inputs
    wheel_filter = NoWheelInputFilter(app)
    app.installEventFilter(wheel_filter)
    app._no_wheel_filter = wheel_filter

    # 4. Install hover-persistent interactive tooltips with clickable man-page links
    from linux_gui_core.widgets.tooltips import install_interactive_tooltips
    install_interactive_tooltips(app)
