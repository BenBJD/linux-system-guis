"""Entrypoint for sysctl-gui."""

import sys
from PyQt6.QtWidgets import QApplication
from linux_gui_core.theme import apply_theme
from sysctl_gui.ui import SysctlMainWindow


def main() -> None:
    app = QApplication(sys.argv)
    apply_theme(app)
    window = SysctlMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
