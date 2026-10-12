"""Entrypoint for udev-gui."""

import sys
from PyQt6.QtWidgets import QApplication
from linux_gui_core.theme import apply_theme
from udev_gui.ui import UdevMainWindow


def main() -> None:
    app = QApplication(sys.argv)
    apply_theme(app)
    window = UdevMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
