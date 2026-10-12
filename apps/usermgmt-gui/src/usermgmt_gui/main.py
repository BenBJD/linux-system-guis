"""Entrypoint for usermgmt-gui."""

import sys
from PyQt6.QtWidgets import QApplication
from linux_gui_core.theme import apply_theme
from usermgmt_gui.ui import UserMgmtMainWindow


def main() -> None:
    app = QApplication(sys.argv)
    apply_theme(app)
    window = UserMgmtMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
