"""Live preview banner widget displaying real-time entry lines and terminal commands."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class LivePreviewBanner(QFrame):
    """A top-of-window banner that dynamically updates in real time to show the exact

    entry or command being generated as the user toggles options.
    """

    diffRequested = pyqtSignal()

    def __init__(
        self,
        title: str = "Live Entry Preview",
        subtitle: str = "Changes below update this line in real-time. Hover over any checkbox for details.",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("livePreviewBanner")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            """
            #livePreviewBanner {
                background-color: #11111b;
                border: 2px solid #89b4fa;
                border-radius: 10px;
                padding: 10px;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        self.title_label = QLabel(f"{title}")
        self.title_label.setStyleSheet("font-weight: bold; color: #89b4fa; font-size: 13px; letter-spacing: 0.5px;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.btn_copy = QPushButton("Copy Line")
        self.btn_copy.setToolTip("Copy this exact line or command to the clipboard to use in terminal")
        self.btn_copy.setFixedHeight(26)
        self.btn_copy.clicked.connect(self._copy_to_clipboard)
        header_layout.addWidget(self.btn_copy)

        self.btn_diff = QPushButton("Compare Diff")
        self.btn_diff.setToolTip("View side-by-side comparison with the existing system configuration")
        self.btn_diff.setFixedHeight(26)
        self.btn_diff.clicked.connect(self.diffRequested.emit)
        header_layout.addWidget(self.btn_diff)

        layout.addLayout(header_layout)

        # Monospace live code box
        self.code_display = QTextEdit()
        self.code_display.setReadOnly(True)
        self.code_display.setFixedHeight(46)
        self.code_display.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.code_display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        mono_font = QFont("JetBrains Mono", 11)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        self.code_display.setFont(mono_font)
        self.code_display.setStyleSheet(
            """
            QTextEdit {
                background-color: #181825;
                color: #a6e3a1;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 6px;
                font-weight: 500;
            }
            """
        )
        layout.addWidget(self.code_display)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet("color: #a6adc8; font-size: 11px; font-style: italic;")
        layout.addWidget(self.subtitle_label)

    def set_text(self, text: str) -> None:
        """Update the live text display."""
        self.code_display.setPlainText(text.strip())

    def get_text(self) -> str:
        """Return the current displayed text."""
        return self.code_display.toPlainText()

    def set_title(self, title: str) -> None:
        self.title_label.setText(f"{title}")

    def set_subtitle(self, subtitle: str) -> None:
        """Update the subtitle explanation."""
        self.subtitle_label.setText(subtitle)

    def _copy_to_clipboard(self) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(self.get_text())
            original_text = self.btn_copy.text()
            self.btn_copy.setText("Copied!")
            self.btn_copy.setStyleSheet("background-color: #a6e3a1; color: #11111b; font-weight: bold;")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: self._reset_copy_btn(original_text))

    def _reset_copy_btn(self, original_text: str) -> None:
        self.btn_copy.setText(original_text)
