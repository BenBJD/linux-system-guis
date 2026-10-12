"""Entrypoint for sudoers-gui."""

import sys
from PyQt6.QtWidgets import QApplication
from linux_gui_core.theme import apply_theme
from sudoers_gui.ui import SudoersMainWindow


def main() -> None:
    app = QApplication(sys.argv)
    apply_theme(app)
    window = SudoersMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
