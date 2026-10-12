"""Entrypoint for permissions-gui."""

import sys
from PyQt6.QtWidgets import QApplication
from linux_gui_core.theme import apply_theme
from permissions_gui.ui import PermissionsMainWindow


def main() -> None:
    app = QApplication(sys.argv)
    apply_theme(app)
    window = PermissionsMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
