"""Entrypoint for device-gui."""

import sys
from PyQt6.QtWidgets import QApplication
from linux_gui_core.theme import apply_theme
from device_gui.ui import DeviceMainWindow


def main() -> None:
    app = QApplication(sys.argv)
    apply_theme(app)
    window = DeviceMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
