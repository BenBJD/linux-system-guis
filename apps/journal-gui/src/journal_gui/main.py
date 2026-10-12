"""Entrypoint for journal-gui."""

import sys
from PyQt6.QtWidgets import QApplication
from linux_gui_core.theme import apply_theme
from journal_gui.ui import JournalMainWindow


def main() -> None:
    app = QApplication(sys.argv)
    apply_theme(app)
    window = JournalMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
