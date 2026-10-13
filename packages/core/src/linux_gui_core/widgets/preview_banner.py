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

from linux_gui_core.strings import tr


class LivePreviewBanner(QFrame):
    """A top-of-window banner that dynamically updates in real time to show the exact
    entry or command being generated as the user toggles options.
    """

    diffRequested = pyqtSignal()

    def __init__(
        self,
        title: str | None = None,
        subtitle: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        if title is None:
            title = tr("banner_default_title")
        if subtitle is None:
            subtitle = tr("banner_default_subtitle")
        self.setObjectName("livePreviewBanner")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            """
            #livePreviewBanner {
                background-color: #222428;
                border: 1px solid #3a3d45;
                border-left: 3px solid #3574d4;
                border-radius: 4px;
                padding: 6px;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(4)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)

        self.title_label = QLabel(f"{title}")
        self.title_label.setStyleSheet("font-weight: bold; color: #6899e6; font-size: 12px; letter-spacing: 0.3px;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.btn_copy = QPushButton(tr("banner_btn_copy"))
        self.btn_copy.setToolTip(tr("banner_btn_copy_tooltip"))
        self.btn_copy.setFixedHeight(22)
        self.btn_copy.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        self.btn_copy.clicked.connect(self._copy_to_clipboard)
        header_layout.addWidget(self.btn_copy)

        self.btn_diff = QPushButton(tr("banner_btn_diff"))
        self.btn_diff.setToolTip(tr("banner_btn_diff_tooltip"))
        self.btn_diff.setFixedHeight(22)
        self.btn_diff.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        self.btn_diff.clicked.connect(self.diffRequested.emit)
        header_layout.addWidget(self.btn_diff)

        layout.addLayout(header_layout)

        # Monospace live code box
        self.code_display = QTextEdit()
        self.code_display.setReadOnly(True)
        self.code_display.setFixedHeight(36)
        self.code_display.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.code_display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        mono_font = QFont("JetBrains Mono", 10)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        self.code_display.setFont(mono_font)
        self.code_display.setStyleSheet(
            """
            QTextEdit {
                background-color: #18191c;
                color: #57ab5a;
                border: 1px solid #2d3036;
                border-radius: 3px;
                padding: 4px;
                font-weight: 500;
            }
            """
        )
        layout.addWidget(self.code_display)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet("color: #9498a1; font-size: 10px; font-style: italic;")
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
            self.btn_copy.setText(tr("banner_btn_copied"))
            self.btn_copy.setStyleSheet("background-color: #2da44e; color: #ffffff; font-weight: bold; font-size: 11px;")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: self._reset_copy_btn(original_text))

    def _reset_copy_btn(self, original_text: str) -> None:
        self.btn_copy.setText(original_text)
        self.btn_copy.setStyleSheet("font-size: 11px; padding: 2px 8px;")
