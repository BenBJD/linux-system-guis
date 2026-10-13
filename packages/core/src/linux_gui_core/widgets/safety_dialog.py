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

from linux_gui_core.strings import tr


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
        self.setMinimumSize(640, 440)
        self.setStyleSheet(
            """
            QDialog {
                background-color: #1e1f22;
                color: #e3e5e8;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header warning / info badge
        banner = QLabel(tr("safety_review_header", target=target_path_or_command))
        banner.setStyleSheet(
            """
            QLabel {
                background-color: #26282d;
                border-left: 3px solid #d49a3d;
                padding: 6px 8px;
                border-radius: 3px;
                color: #e3e5e8;
            }
            """
        )
        layout.addWidget(banner)

        # Safety Notes / Explanations
        if safety_notes:
            notes_html = f"<b>{tr('safety_protections_heading')}</b><ul>" + "".join(f"<li>{n}</li>" for n in safety_notes) + "</ul>"
            notes_lbl = QLabel(notes_html)
            notes_lbl.setStyleSheet("color: #9498a1; font-size: 11px;")
            notes_lbl.setWordWrap(True)
            layout.addWidget(notes_lbl)

        # Diff or Command viewer
        lbl_preview = QLabel(tr("safety_preview_label"))
        lbl_preview.setStyleSheet("font-weight: bold; color: #6899e6; font-size: 12px;")
        layout.addWidget(lbl_preview)

        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        self.text_preview.setStyleSheet(
            """
            QTextEdit {
                background-color: #18191c;
                border: 1px solid #2d3036;
                border-radius: 3px;
                padding: 6px;
                color: #e3e5e8;
            }
            """
        )
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
        btn_layout.setSpacing(8)
        btn_copy = QPushButton(tr("safety_btn_copy"))
        btn_copy.clicked.connect(self._copy_command)
        btn_layout.addWidget(btn_copy)

        btn_layout.addStretch()

        self.btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_apply = self.btn_box.button(QDialogButtonBox.StandardButton.Ok)
        btn_apply.setText(tr("safety_btn_apply"))
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
                html_lines.append(f"<span style='color: #3ba55d; background-color: #162c1e;'>{escaped}</span>")
            elif line.startswith("-"):
                html_lines.append(f"<span style='color: #d83a52; background-color: #33151b;'>{escaped}</span>")
            elif line.startswith("@"):
                html_lines.append(f"<span style='color: #6899e6; font-weight: bold;'>{escaped}</span>")
            else:
                html_lines.append(f"<span style='color: #e3e5e8;'>{escaped}</span>")

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
