"""Widget displaying package ownership status and warnings for system files."""

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget
from linux_gui_core.runner.package_manager import PackageOwnership


class PackageOwnershipBadge(QFrame):
    """Pill badge showing whether a file is tracked by pacman, dpkg, rpm, or unmanaged."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 4, 8, 4)
        self.layout.setSpacing(6)

        self.label = QLabel("Checking package status...")
        self.layout.addWidget(self.label)
        self.set_unmanaged("custom")

    def update_status(self, ownership: PackageOwnership, file_path: str = "") -> None:
        """Update badge appearance based on package ownership."""
        if ownership.is_managed:
            pkg_str = ownership.package_name or "Unknown"
            if ownership.package_version:
                pkg_str += f" ({ownership.package_version})"

            self.label.setText(f"Managed by package: {pkg_str}")
            self.setStyleSheet(
                """
                QFrame {
                    background-color: #3e2e1e;
                    border: 1px solid #f9e2af;
                    border-radius: 6px;
                }
                QLabel {
                    color: #f9e2af;
                    font-size: 11px;
                    font-weight: bold;
                }
                """
            )
            self.setToolTip(
                f"<div style='max-width: 320px; line-height: 1.4;'>"
                f"<b style='color: #f9e2af;'>Package-Managed File Detected</b><br>"
                f"<span style='font-family: monospace;'>{file_path}</span><br><br>"
                f"This file is owned and maintained by the <b>{ownership.package_name}</b> package "
                f"(via <i>{ownership.package_manager}</i>).<br><br>"
                f"<b>Why this matters:</b><br>"
                f"Editing this file directly may be overwritten during future package updates, "
                f"or result in configuration merge conflicts (such as .pacnew or .dpkg-dist files). "
                f"Consider creating a separate override file if supported (e.g. 99-custom.rules)."
                f"</div>"
            )
        else:
            pm_name = ownership.package_manager or "system package manager"
            self.label.setText("✓ 👤 Custom / User-Created File")
            self.setStyleSheet(
                """
                QFrame {
                    background-color: #1e3a2f;
                    border: 1px solid #a6e3a1;
                    border-radius: 6px;
                }
                QLabel {
                    color: #a6e3a1;
                    font-size: 11px;
                    font-weight: bold;
                }
                """
            )
            self.setToolTip(
                f"<div style='max-width: 300px; line-height: 1.4;'>"
                f"<b style='color: #a6e3a1;'>✓ Unmanaged Configuration File</b><br>"
                f"This file is not tracked by {pm_name}. It was created locally and "
                f"can be safely edited or deleted without conflicting with system packages."
                f"</div>"
            )

    def set_unmanaged(self, note: str = "") -> None:
        self.label.setText("Custom / User-Created File")
        self.setStyleSheet(
            """
            QFrame {
                background-color: #1e3a2f;
                border: 1px solid #a6e3a1;
                border-radius: 6px;
            }
            QLabel {
                color: #a6e3a1;
                font-size: 11px;
                font-weight: bold;
            }
            """
        )
