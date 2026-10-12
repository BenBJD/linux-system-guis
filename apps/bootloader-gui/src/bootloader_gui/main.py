"""Entrypoint for bootloader-gui."""

import sys
from PyQt6.QtWidgets import QApplication
from linux_gui_core.theme import apply_theme
from bootloader_gui.ui import BootloaderMainWindow


def main() -> None:
    app = QApplication(sys.argv)
    apply_theme(app)
    window = BootloaderMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
