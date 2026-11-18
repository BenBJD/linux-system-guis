"""Central launcher dashboard for Linux System GUIs."""

import sys
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from linux_gui_core.theme import apply_theme
from linux_gui_core.widgets.loading_modal import LoadingModal
from linux_system_guis.strings import tr
from fstab_gui.ui import FstabMainWindow
from udev_gui.ui import UdevMainWindow
from systemd_gui.ui import SystemdMainWindow
from usermgmt_gui.ui import UserMgmtMainWindow
from sudoers_gui.ui import SudoersMainWindow
from journal_gui.ui import JournalMainWindow
from sysctl_gui.ui import SysctlMainWindow
from permissions_gui.ui import PermissionsMainWindow
from bootloader_gui.ui import BootloaderMainWindow
from device_gui.ui import DeviceMainWindow


class LauncherCard(QFrame):
    """A compact list row representing an individual administration tool."""

    def __init__(self, title: str, icon: str, category: str, desc: str, on_launch, parent=None):
        super().__init__(parent)
        self._on_launch = on_launch
        self.setObjectName("launcherCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            """
            QFrame#launcherCard {
                background-color: #1a1d24;
                border: 1px solid #282d38;
                border-radius: 6px;
            }
            QFrame#launcherCard:hover {
                border-color: #388bfd;
                background-color: #202530;
            }
            QLabel {
                border: none;
                background: transparent;
            }
            """
        )

        row_layout = QHBoxLayout(self)
        row_layout.setContentsMargins(14, 10, 14, 10)
        row_layout.setSpacing(14)

        # 0: Icon
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 22px; border: none; background: transparent;")
        icon_lbl.setFixedWidth(32)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row_layout.addWidget(icon_lbl)

        # Title & Category Box (fixed width to align descriptions neatly)
        title_box = QVBoxLayout()
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.setSpacing(2)

        # 1: Category
        cat_lbl = QLabel(category.upper())
        cat_lbl.setStyleSheet(
            "font-size: 10.5px; font-weight: 700; color: #85abf2; letter-spacing: 0.6px; border: none; background: transparent;"
        )
        title_box.addWidget(cat_lbl)

        # 2: Title
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #f0f3f6; border: none; background: transparent;")
        title_box.addWidget(title_lbl)

        title_container = QWidget()
        title_container.setStyleSheet("border: none; background: transparent;")
        title_container.setLayout(title_box)
        title_container.setFixedWidth(250)
        row_layout.addWidget(title_container)

        # 3: Description
        desc_lbl = QLabel(desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #9198a1; font-size: 12.5px; line-height: 1.4; border: none; background: transparent;")
        row_layout.addWidget(desc_lbl, stretch=1)

        # Open Button
        btn_launch = QPushButton(tr("btn_open"))
        btn_launch.setObjectName("primaryBtn")
        btn_launch.setFixedHeight(28)
        btn_launch.setFixedWidth(74)
        btn_launch.setStyleSheet("font-size: 12px; font-weight: 600; padding: 3px 10px;")
        btn_launch.clicked.connect(self._on_launch)
        row_layout.addWidget(btn_launch)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self._on_launch()
        super().mouseReleaseEvent(event)


class LauncherMainWindow(QMainWindow):
    """Main launcher hub for the Linux System GUIs administration suite."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("window_title"))
        self.resize(1280, 720)
        self.setMinimumSize(800, 500)
        self.windows: list[QMainWindow] = []
        self.cards: list[LauncherCard] = []

        self._init_ui()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Header Title Bar
        title_bar = QHBoxLayout()
        title_bar.setSpacing(10)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)

        title = QLabel(tr("header_title"))
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #f0f3f6;")
        title_col.addWidget(title)

        subtitle = QLabel(
            "Safe, transparent desktop tools for low-level system configuration. "
            "Real-time command previews, dry-run checks, and detailed tooltips."
        )
        subtitle.setStyleSheet("color: #9198a1; font-size: 13px;")
        title_col.addWidget(subtitle)

        title_bar.addLayout(title_col, stretch=1)

        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText(tr("filter_placeholder"))
        self.txt_filter.setMaximumWidth(280)
        self.txt_filter.setClearButtonEnabled(True)
        self.txt_filter.textChanged.connect(self._filter_cards)
        title_bar.addWidget(self.txt_filter)

        layout.addLayout(title_bar)

        # Scrollable List of App Rows
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        self.list_layout = QVBoxLayout(container)
        self.list_layout.setContentsMargins(2, 4, 6, 4)
        self.list_layout.setSpacing(6)

        # Tool definitions: (string-key prefix, icon, launch callback)
        tools = [
            ("tool_device", "🖥️", self.launch_device),
            ("tool_fstab", "💾", self.launch_fstab),
            ("tool_udev", "🔌", self.launch_udev),
            ("tool_systemd", "⚙️", self.launch_systemd),
            ("tool_usermgmt", "👥", self.launch_usermgmt),
            ("tool_sudoers", "🛡️", self.launch_sudoers),
            ("tool_journal", "📜", self.launch_journal),
            ("tool_sysctl", "🧠", self.launch_sysctl),
            ("tool_permissions", "🔓", self.launch_permissions),
            ("tool_bootloader", "🚀", self.launch_bootloader),
        ]
        card_data = [
            (tr(f"{key}_title"), icon, tr(f"{key}_category"), tr(f"{key}_desc"), callback)
            for key, icon, callback in tools
        ]

        for t, icon, cat, desc, callback in card_data:
            card = LauncherCard(t, icon, cat, desc, callback)
            self.cards.append(card)
            self.list_layout.addWidget(card)

        self.list_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _filter_cards(self, text: str) -> None:
        needle = text.lower().strip()
        for card in self.cards:
            labels = card.findChildren(QLabel)
            if len(labels) >= 4:
                matches = (
                    needle in labels[1].text().lower()
                    or needle in labels[2].text().lower()
                    or needle in labels[3].text().lower()
                )
            else:
                matches = True
            card.setVisible(matches)

    def _open_tool_window(self, window_cls, title: str, subtitle: str) -> QMainWindow:
        modal: LoadingModal | None = None
        if self.isVisible():
            modal = LoadingModal(
                title=f"Opening {title}...",
                subtitle=subtitle,
                parent=self,
            )
            LoadingModal._active_instance = modal
            modal.sync_to_parent()
            modal.show()
            modal.raise_()
            QApplication.processEvents()

        try:
            win = window_cls()
        finally:
            if modal is not None:
                if LoadingModal._active_instance is modal:
                    LoadingModal._active_instance = None
                modal.hide()
                modal.deleteLater()

        win.show()
        self.windows.append(win)
        return win

    def launch_device(self) -> None:
        self._open_tool_window(
            DeviceMainWindow,
            tr("tool_device_title"),
            "Scanning PCI, USB, sysfs, and kernel driver modules...",
        )

    def launch_fstab(self) -> None:
        self._open_tool_window(
            FstabMainWindow,
            tr("tool_fstab_title"),
            "Reading /etc/fstab mount table...",
        )

    def launch_udev(self) -> None:
        self._open_tool_window(
            UdevMainWindow,
            tr("tool_udev_title"),
            "Loading udev rules and package ownership...",
        )

    def launch_systemd(self) -> None:
        self._open_tool_window(
            SystemdMainWindow,
            tr("tool_systemd_title"),
            "Querying systemd service units and timer schedules...",
        )

    def launch_usermgmt(self) -> None:
        self._open_tool_window(
            UserMgmtMainWindow,
            tr("tool_usermgmt_title"),
            "Reading /etc/passwd and /etc/group accounts...",
        )

    def launch_sudoers(self) -> None:
        self._open_tool_window(
            SudoersMainWindow,
            tr("tool_sudoers_title"),
            "Inspecting /etc/sudoers and /etc/sudoers.d rules...",
        )

    def launch_journal(self) -> None:
        self._open_tool_window(
            JournalMainWindow,
            tr("tool_journal_title"),
            "Querying systemd-journald boot sessions and log entries...",
        )

    def launch_sysctl(self) -> None:
        self._open_tool_window(
            SysctlMainWindow,
            tr("tool_sysctl_title"),
            "Reading live kernel parameters from /proc/sys...",
        )

    def launch_permissions(self) -> None:
        self._open_tool_window(
            PermissionsMainWindow,
            tr("tool_permissions_title"),
            "Inspecting POSIX ACLs and filesystem attributes...",
        )

    def launch_bootloader(self) -> None:
        self._open_tool_window(
            BootloaderMainWindow,
            tr("tool_bootloader_title"),
            "Detecting bootloader architecture and kernel parameters...",
        )


def main() -> None:
    app = QApplication(sys.argv)
    apply_theme(app)
    launcher = LauncherMainWindow()
    launcher.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
