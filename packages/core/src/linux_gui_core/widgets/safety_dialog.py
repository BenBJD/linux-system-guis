"""Safety inspection modal before applying system changes."""

import difflib
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class SafetyExecutionDialog(QDialog):
    """Modal that enforces transparency: shows the exact command or file modification

    with side-by-side or unified diff, safety check explanations, and dry-run execution.
    """

    def __init__(
        self,
        title: str,
        target_path_or_command: str,
        diff_text: str | None = None,
        safety_notes: list[str] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(680, 480)
        self.setStyleSheet(
            """
            QDialog {
                background-color: #1e1e2e;
                color: #cdd6f4;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header warning / info badge
        banner = QLabel(f"⚠️ <b>Review System Changes</b><br>Target: <code>{target_path_or_command}</code>")
        banner.setStyleSheet(
            """
            QLabel {
                background-color: #313244;
                border-left: 4px solid #f9e2af;
                padding: 10px;
                border-radius: 6px;
                color: #cdd6f4;
            }
            """
        )
        layout.addWidget(banner)

        # Safety Notes / Explanations
        if safety_notes:
            notes_html = "<b>Safety Protections:</b><ul>" + "".join(f"<li>{n}</li>" for n in safety_notes) + "</ul>"
            notes_lbl = QLabel(notes_html)
            notes_lbl.setStyleSheet("color: #a6adc8; font-size: 12px;")
            notes_lbl.setWordWrap(True)
            layout.addWidget(notes_lbl)

        # Diff or Command viewer
        lbl_preview = QLabel("Planned Changes / Command Execution:")
        lbl_preview.setStyleSheet("font-weight: bold; color: #89b4fa;")
        layout.addWidget(lbl_preview)

        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        mono_font = QFont("JetBrains Mono", 10)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        self.text_preview.setFont(mono_font)

        if diff_text:
            self._render_colorized_diff(diff_text)
        else:
            self.text_preview.setPlainText(target_path_or_command)

        layout.addWidget(self.text_preview)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_copy = QPushButton("📋 Copy Command")
        btn_copy.clicked.connect(self._copy_command)
        btn_layout.addWidget(btn_copy)

        btn_layout.addStretch()

        self.btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_apply = self.btn_box.button(QDialogButtonBox.StandardButton.Ok)
        btn_apply.setText("Apply Changes (Requires Root)")
        btn_apply.setObjectName("primaryBtn")
        self.btn_box.accepted.connect(self.accept)
        self.btn_box.rejected.connect(self.reject)
        btn_layout.addWidget(self.btn_box)

        layout.addLayout(btn_layout)

    def _render_colorized_diff(self, diff_text: str) -> None:
        """Render unified diff with green and red highlighting."""
        html_lines = []
        for line in diff_text.splitlines():
            escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if line.startswith("+"):
                html_lines.append(f"<span style='color: #a6e3a1; background-color: #1e3a2f;'>{escaped}</span>")
            elif line.startswith("-"):
                html_lines.append(f"<span style='color: #f38ba8; background-color: #3f1d28;'>{escaped}</span>")
            elif line.startswith("@"):
                html_lines.append(f"<span style='color: #89b4fa; font-weight: bold;'>{escaped}</span>")
            else:
                html_lines.append(f"<span style='color: #cdd6f4;'>{escaped}</span>")

        self.text_preview.setHtml("<br>".join(html_lines))

    def _copy_command(self) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(self.text_preview.toPlainText())


def generate_diff(original: str, modified: str, filename: str = "file") -> str:
    """Generate a clean unified diff string between original and modified text."""
    orig_lines = original.splitlines(keepends=True)
    mod_lines = modified.splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_lines,
        mod_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
    )
    return "".join(diff)
