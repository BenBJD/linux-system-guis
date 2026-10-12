"""Entrypoint for systemd-gui."""

import sys
from PyQt6.QtWidgets import QApplication
from linux_gui_core.theme import apply_theme
from systemd_gui.ui import SystemdMainWindow


def main() -> None:
    app = QApplication(sys.argv)
    apply_theme(app)
    window = SystemdMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
