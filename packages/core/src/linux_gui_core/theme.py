"""Desktop styling, theme definitions, and UX protections for Linux System GUIs."""

import os
import re
from PyQt6.QtCore import QEvent, QObject
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QToolButton,
)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
DOWN_ARROW_PATH = os.path.join(ASSETS_DIR, "down_arrow.svg").replace("\\", "/")
UP_ARROW_PATH = os.path.join(ASSETS_DIR, "up_arrow.svg").replace("\\", "/")


def _escape_button_ampersands() -> None:
    """Ensures literal '&' in button and checkbox labels renders correctly
    instead of being treated by Qt as a keyboard mnemonic/shortcut character.
    """
    for cls in (QPushButton, QToolButton, QCheckBox, QRadioButton):
        if getattr(cls, "_amp_patched", False):
            continue
        orig_init = cls.__init__
        orig_setText = cls.setText

        def _esc(val):
            if isinstance(val, str):
                return re.sub(r"(?<!&)&(?!&)", "&&", val)
            return val

        def _make_init(old_init):
            def patched_init(self, *args, **kwargs):
                new_args = list(args)
                if len(new_args) >= 1 and isinstance(new_args[0], str):
                    new_args[0] = _esc(new_args[0])
                elif len(new_args) >= 2 and isinstance(new_args[1], str):
                    new_args[1] = _esc(new_args[1])
                if "text" in kwargs and isinstance(kwargs["text"], str):
                    kwargs["text"] = _esc(kwargs["text"])
                old_init(self, *new_args, **kwargs)
            return patched_init

        def _make_setText(old_setText):
            def patched_setText(self, text):
                old_setText(self, _esc(text))
            return patched_setText

        cls.__init__ = _make_init(orig_init)
        cls.setText = _make_setText(orig_setText)
        cls._amp_patched = True


# Run immediately on module import so any buttons created before apply_theme are protected
_escape_button_ampersands()


def build_stylesheet() -> str:
    return f"""
QMainWindow, QDialog, QScrollArea, QSplitter {{
    background-color: #1e1f22;
    color: #e3e5e8;
}}

/* Ensure all scroll areas and viewport containers have consistent dark background */
QScrollArea,
QScrollArea > QWidget,
QScrollArea > QWidget > QWidget,
QScrollArea QWidget#qt_scrollarea_viewport {{
    background-color: #1e1f22;
    border: none;
}}

QWidget {{
    font-family: 'Inter', 'Cantarell', 'Noto Sans', 'Segoe UI', sans-serif;
    font-size: 12px;
    color: #e3e5e8;
}}

QGroupBox {{
    font-weight: bold;
    font-size: 12px;
    border: 1px solid #3a3d45;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 10px;
    padding-bottom: 6px;
    padding-left: 8px;
    padding-right: 8px;
    background-color: #1e1f22;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 4px;
    color: #6899e6;
}}

QPushButton {{
    background-color: #2b2d33;
    color: #e3e5e8;
    border: 1px solid #3d4048;
    border-radius: 3px;
    padding: 4px 10px;
    font-weight: 500;
    font-size: 12px;
}}

QPushButton:hover {{
    background-color: #373a42;
    border-color: #4c505a;
}}

QPushButton:pressed {{
    background-color: #222428;
}}

QPushButton#primaryBtn {{
    background-color: #3574d4;
    color: #ffffff;
    border: 1px solid #4382e2;
    font-weight: 600;
}}

QPushButton#primaryBtn:hover {{
    background-color: #4382e2;
}}

QPushButton#primaryBtn:pressed {{
    background-color: #2961b5;
}}

QPushButton#dangerBtn {{
    background-color: #bd3646;
    color: #ffffff;
    border: 1px solid #cc4151;
    font-weight: 600;
}}

QPushButton#dangerBtn:hover {{
    background-color: #cc4151;
}}

QPushButton#dangerBtn:pressed {{
    background-color: #9e2837;
}}

QLineEdit {{
    background-color: #18191c;
    border: 1px solid #3a3d45;
    border-radius: 3px;
    padding: 4px 6px;
    color: #e3e5e8;
    selection-background-color: #3574d4;
    selection-color: #ffffff;
    font-size: 12px;
}}

QLineEdit:focus {{
    border: 1px solid #3574d4;
}}

/* ComboBox with visible drop-down indicator arrow */
QComboBox {{
    background-color: #18191c;
    border: 1px solid #3a3d45;
    border-radius: 3px;
    padding: 4px 22px 4px 6px;
    color: #e3e5e8;
    selection-background-color: #3574d4;
    selection-color: #ffffff;
    font-size: 12px;
}}

QComboBox:focus {{
    border: 1px solid #3574d4;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #3a3d45;
    border-top-right-radius: 3px;
    border-bottom-right-radius: 3px;
    background-color: #18191c;
}}

QComboBox::drop-down:hover {{
    background-color: #2b2d33;
}}

QComboBox::down-arrow {{
    image: url("{DOWN_ARROW_PATH}");
    width: 9px;
    height: 5px;
}}

QComboBox QAbstractItemView {{
    background-color: #18191c;
    border: 1px solid #3a3d45;
    border-radius: 3px;
    color: #e3e5e8;
    selection-background-color: #2e3b52;
    selection-color: #ffffff;
    padding: 2px;
}}

/* SpinBox with up and down buttons and arrows */
QSpinBox, QDoubleSpinBox {{
    background-color: #18191c;
    border: 1px solid #3a3d45;
    border-radius: 3px;
    padding: 4px 18px 4px 6px;
    color: #e3e5e8;
    selection-background-color: #3574d4;
    selection-color: #ffffff;
    font-size: 12px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid #3574d4;
}}

QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 16px;
    border-left: 1px solid #3a3d45;
    border-bottom: 1px solid #3a3d45;
    border-top-right-radius: 3px;
    background-color: #18191c;
}}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
    background-color: #2b2d33;
}}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url("{UP_ARROW_PATH}");
    width: 7px;
    height: 4px;
}}

QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 16px;
    border-left: 1px solid #3a3d45;
    border-bottom-right-radius: 3px;
    background-color: #18191c;
}}

QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: #2b2d33;
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url("{DOWN_ARROW_PATH}");
    width: 7px;
    height: 4px;
}}

QCheckBox {{
    spacing: 6px;
    color: #e3e5e8;
    background: transparent;
    font-size: 12px;
}}

QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border-radius: 2px;
    border: 1px solid #4e525c;
    background-color: #18191c;
}}

QCheckBox::indicator:checked {{
    background-color: #3574d4;
    border: 1px solid #4382e2;
}}

QTableWidget, QTreeWidget, QListWidget {{
    background-color: #18191c;
    border: 1px solid #2d3036;
    border-radius: 4px;
    gridline-color: #26282d;
    color: #e3e5e8;
    selection-background-color: #28374f;
    selection-color: #ffffff;
}}

QHeaderView::section {{
    background-color: #222428;
    color: #9498a1;
    padding: 4px 6px;
    font-weight: 600;
    font-size: 11px;
    border: none;
    border-bottom: 1px solid #2d3036;
}}

QTabWidget::pane {{
    border: 1px solid #2d3036;
    border-radius: 4px;
    background-color: #1e1f22;
    padding: 6px;
}}

QTabBar::tab {{
    background-color: #18191c;
    color: #9498a1;
    padding: 4px 12px;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
    margin-right: 2px;
    font-size: 12px;
}}

QTabBar::tab:selected {{
    background-color: #2b2d33;
    color: #ffffff;
    font-weight: 600;
}}

QScrollBar:vertical {{
    background: #18191c;
    width: 8px;
    margin: 0;
    border-radius: 2px;
}}

QScrollBar::handle:vertical {{
    background: #3a3d45;
    min-height: 16px;
    border-radius: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background: #4e525c;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QSplitter::handle {{
    background-color: #2d3036;
}}

QToolTip {{
    background-color: #18191c;
    color: #e3e5e8;
    border: 1px solid #3a3d45;
    padding: 4px 8px;
    border-radius: 3px;
    font-size: 11px;
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
    palette.setColor(QPalette.ColorRole.Window, QColor("#1e1f22"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#e3e5e8"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#18191c"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1e1f22"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#e3e5e8"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#2b2d33"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e3e5e8"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#3574d4"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    # 2. Stylesheet
    app.setStyleSheet(build_stylesheet())

    # 3. Disable mouse scrolling value mutation on inputs
    wheel_filter = NoWheelInputFilter(app)
    app.installEventFilter(wheel_filter)
    app._no_wheel_filter = wheel_filter
