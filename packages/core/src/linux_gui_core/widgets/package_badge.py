"""Widget displaying package ownership status and warnings for system files."""

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget
from linux_gui_core.runner.package_manager import PackageOwnership
from linux_gui_core.strings import tr

_MANAGED_STYLE = """
    QFrame {
        background-color: #33271a;
        border: 1px solid #735429;
        border-radius: 3px;
    }
    QLabel {
        color: #d49a3d;
        font-size: 11px;
        font-weight: 600;
    }
"""

_UNMANAGED_STYLE = """
    QFrame {
        background-color: #172d1f;
        border: 1px solid #2b5e3d;
        border-radius: 3px;
    }
    QLabel {
        color: #57ab5a;
        font-size: 11px;
        font-weight: 600;
    }
"""


class PackageOwnershipBadge(QFrame):
    """Pill badge showing whether a file is tracked by pacman, dpkg, rpm, or unmanaged."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(6, 2, 6, 2)
        self.layout.setSpacing(4)

        self.label = QLabel(tr("badge_checking"))
        self.layout.addWidget(self.label)
        self.set_unmanaged("custom")

    def update_status(self, ownership: PackageOwnership, file_path: str = "") -> None:
        """Update badge appearance based on package ownership."""
        if ownership.is_managed:
            pkg_str = ownership.package_name or tr("badge_unknown_package")
            if ownership.package_version:
                pkg_str += f" ({ownership.package_version})"

            self.label.setText(tr("badge_managed_by", package=pkg_str))
            self.setStyleSheet(_MANAGED_STYLE)
            self.setToolTip(
                tr(
                    "badge_managed_tooltip",
                    path=file_path,
                    package=ownership.package_name,
                    manager=ownership.package_manager,
                )
            )
        else:
            pm_name = ownership.package_manager or tr("badge_default_manager")
            self.label.setText(tr("badge_user_created"))
            self.setStyleSheet(_UNMANAGED_STYLE)
            self.setToolTip(tr("badge_unmanaged_tooltip", manager=pm_name))

    def set_unmanaged(self, note: str = "") -> None:
        self.label.setText(tr("badge_user_created_plain"))
        self.setStyleSheet(_UNMANAGED_STYLE)
