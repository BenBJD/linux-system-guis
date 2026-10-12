"""Entrypoint for fstab-gui."""

import sys
from PyQt6.QtWidgets import QApplication
from linux_gui_core.theme import apply_theme
from fstab_gui.ui import FstabMainWindow


def main() -> None:
    app = QApplication(sys.argv)
    apply_theme(app)
    window = FstabMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
