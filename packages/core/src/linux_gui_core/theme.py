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
    background-color: #1e1e2e;
    color: #cdd6f4;
}}

/* Ensure all scroll areas and viewport containers have consistent dark background */
QScrollArea,
QScrollArea > QWidget,
QScrollArea > QWidget > QWidget,
QScrollArea QWidget#qt_scrollarea_viewport {{
    background-color: #1e1e2e;
    border: none;
}}

QWidget {{
    font-family: 'Inter', 'Cantarell', 'Noto Sans', 'Segoe UI', sans-serif;
    font-size: 13px;
    color: #cdd6f4;
}}

QGroupBox {{
    font-weight: bold;
    border: 1px solid #45475a;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 14px;
    padding-bottom: 8px;
    padding-left: 10px;
    padding-right: 10px;
    background-color: #1e1e2e;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #89b4fa;
}}

QPushButton {{
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: #45475a;
    border-color: #585b70;
}}

QPushButton:pressed {{
    background-color: #585b70;
}}

QPushButton#primaryBtn {{
    background-color: #89b4fa;
    color: #11111b;
    border: 1px solid #74c7ec;
    font-weight: 600;
}}

QPushButton#primaryBtn:hover {{
    background-color: #b4befe;
}}

QPushButton#dangerBtn {{
    background-color: #f38ba8;
    color: #11111b;
    border: 1px solid #eba0ac;
    font-weight: 600;
}}

QPushButton#dangerBtn:hover {{
    background-color: #eba0ac;
}}

QLineEdit {{
    background-color: #181825;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 5px 8px;
    color: #cdd6f4;
    selection-background-color: #89b4fa;
    selection-color: #11111b;
}}

QLineEdit:focus {{
    border: 1px solid #89b4fa;
}}

/* ComboBox with visible drop-down indicator arrow */
QComboBox {{
    background-color: #181825;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 5px 28px 5px 8px;
    color: #cdd6f4;
    selection-background-color: #89b4fa;
    selection-color: #11111b;
}}

QComboBox:focus {{
    border: 1px solid #89b4fa;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #45475a;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    background-color: #181825;
}}

QComboBox::drop-down:hover {{
    background-color: #313244;
}}

QComboBox::down-arrow {{
    image: url("{DOWN_ARROW_PATH}");
    width: 10px;
    height: 6px;
}}

QComboBox QAbstractItemView {{
    background-color: #181825;
    border: 1px solid #45475a;
    border-radius: 6px;
    color: #cdd6f4;
    selection-background-color: #45475a;
    selection-color: #89b4fa;
    padding: 4px;
}}

/* SpinBox with up and down buttons and arrows */
QSpinBox, QDoubleSpinBox {{
    background-color: #181825;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 5px 22px 5px 8px;
    color: #cdd6f4;
    selection-background-color: #89b4fa;
    selection-color: #11111b;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid #89b4fa;
}}

QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 18px;
    border-left: 1px solid #45475a;
    border-bottom: 1px solid #45475a;
    border-top-right-radius: 6px;
    background-color: #181825;
}}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
    background-color: #313244;
}}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url("{UP_ARROW_PATH}");
    width: 8px;
    height: 5px;
}}

QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 18px;
    border-left: 1px solid #45475a;
    border-bottom-right-radius: 6px;
    background-color: #181825;
}}

QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: #313244;
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url("{DOWN_ARROW_PATH}");
    width: 8px;
    height: 5px;
}}

QCheckBox {{
    spacing: 8px;
    color: #cdd6f4;
    background: transparent;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #585b70;
    background-color: #181825;
}}

QCheckBox::indicator:checked {{
    background-color: #89b4fa;
    border: 1px solid #74c7ec;
}}

QTableWidget, QTreeWidget, QListWidget {{
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 8px;
    gridline-color: #313244;
    color: #cdd6f4;
    selection-background-color: #45475a;
    selection-color: #cdd6f4;
}}

QHeaderView::section {{
    background-color: #1e1e2e;
    color: #a6adc8;
    padding: 6px;
    font-weight: bold;
    border: none;
    border-bottom: 1px solid #313244;
}}

QTabWidget::pane {{
    border: 1px solid #313244;
    border-radius: 8px;
    background-color: #1e1e2e;
    padding: 8px;
}}

QTabBar::tab {{
    background-color: #181825;
    color: #a6adc8;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 4px;
}}

QTabBar::tab:selected {{
    background-color: #313244;
    color: #89b4fa;
    font-weight: bold;
}}

QScrollBar:vertical {{
    background: #181825;
    width: 10px;
    margin: 0;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background: #45475a;
    min-height: 20px;
    border-radius: 5px;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QSplitter::handle {{
    background-color: #313244;
}}

QToolTip {{
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #89b4fa;
    padding: 6px;
    border-radius: 6px;
    font-size: 12px;
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
    palette.setColor(QPalette.ColorRole.Window, QColor("#1e1e2e"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#cdd6f4"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#181825"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1e1e2e"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#cdd6f4"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#313244"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#cdd6f4"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#89b4fa"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#11111b"))
    app.setPalette(palette)

    # 2. Stylesheet
    app.setStyleSheet(build_stylesheet())

    # 3. Disable mouse scrolling value mutation on inputs
    wheel_filter = NoWheelInputFilter(app)
    app.installEventFilter(wheel_filter)
    app._no_wheel_filter = wheel_filter
