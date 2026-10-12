"""Central launcher dashboard for Linux System GUIs."""

import sys
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
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
from fstab_gui.ui import FstabMainWindow
from udev_gui.ui import UdevMainWindow
from systemd_gui.ui import SystemdMainWindow
from usermgmt_gui.ui import UserMgmtMainWindow
from sudoers_gui.ui import SudoersMainWindow
from journal_gui.ui import JournalMainWindow
from sysctl_gui.ui import SysctlMainWindow
from permissions_gui.ui import PermissionsMainWindow
from bootloader_gui.ui import BootloaderMainWindow


class LauncherCard(QFrame):
    """A visual card representing an individual administration tool."""

    def __init__(self, title: str, icon: str, category: str, desc: str, on_launch, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            """
            QFrame {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 12px;
                padding: 10px;
            }
            QFrame:hover {
                border-color: #89b4fa;
                background-color: #1e1e2e;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        header = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 26px;")
        header.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        cat_lbl = QLabel(category.upper())
        cat_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #89b4fa;")
        title_col.addWidget(cat_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #cdd6f4;")
        title_col.addWidget(title_lbl)

        header.addLayout(title_col)
        header.addStretch()
        layout.addLayout(header)

        desc_lbl = QLabel(desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #a6adc8; font-size: 14px; line-height: 1.4;")
        layout.addWidget(desc_lbl)

        layout.addStretch()

        btn_launch = QPushButton("🚀 Open Application")
        btn_launch.setObjectName("primaryBtn")
        btn_launch.clicked.connect(on_launch)
        layout.addWidget(btn_launch)


class LauncherMainWindow(QMainWindow):
    """Main launcher hub for the Linux System GUIs administration suite."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Linux System GUIs")
        self.resize(1280, 800)
        self.setMinimumSize(960, 680)
        self.windows: list[QMainWindow] = []
        self.cards: list[LauncherCard] = []

        self._init_ui()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        # Header Title
        title_bar = QHBoxLayout()
        title = QLabel("Linux System GUIs")
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: #cdd6f4;")
        title_bar.addWidget(title)

        title_bar.addStretch()

        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("Filter tools (e.g. logs, sudo, fstab, boot, kernel)...")
        self.txt_filter.setMaximumWidth(320)
        self.txt_filter.textChanged.connect(self._filter_cards)
        title_bar.addWidget(self.txt_filter)

        layout.addLayout(title_bar)

        subtitle = QLabel(
            "Safe, transparent, and educational desktop tools for low-level system configuration. "
            "Every tool displays real-time command/file line previews, dry-run checks, and detailed tooltips."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #a6adc8; font-size: 13px; line-height: 1.4;")
        layout.addWidget(subtitle)

        # Scrollable Grid of 9 App Cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        self.grid = QGridLayout(container)
        self.grid.setSpacing(10)

        # Card definitions
        card_data = [
            (
                "fstab Editor",
                "💾",
                "Disks & Mounts",
                "Manage /etc/fstab mount points, UUIDs, filesystem options (noatime, nosuid, nofail), systemd automounts, and test with mount -fa dry runs.",
                self.launch_fstab,
            ),
            (
                "udev Rules Builder",
                "🔌",
                "Hardware & Devices",
                "Create and modify device rules in /etc/udev/rules.d/ with matching vendor IDs, permission modes (0666), sleep wakeup toggles, uaccess tags, and daemon reloads.",
                self.launch_udev,
            ),
            (
                "systemd Services & Timers",
                "⚙️",
                "Init & Daemons",
                "Explore, start, stop, enable system & user services with friendly status tags (Running, Stopped, Starts on Boot). Build scheduled timers with OnCalendar expressions.",
                self.launch_systemd,
            ),
            (
                "Users & Groups Security",
                "👥",
                "Access Control",
                "Manage user accounts, login shells (/bin/bash vs /usr/bin/nologin), and full system group memberships (vboxusers, ollama, sudo, docker) with real-time usermod command preview.",
                self.launch_usermgmt,
            ),
            (
                "Sudoers Privilege Manager",
                "🛡️",
                "Privilege Delegation",
                "Configure sudoers rules in /etc/sudoers.d/ for users and groups (%wheel). Pick passwordless commands (NOPASSWD) with automated visudo -c syntax validation.",
                self.launch_sudoers,
            ),
            (
                "System Journal & Logs",
                "📜",
                "Diagnostics & Maintenance",
                "Explore system and service logs with journalctl. Filter by boot sessions (-b), units (-u), log levels (-p), and vacuum old logs by time or disk size.",
                self.launch_journal,
            ),
            (
                "Kernel Parameters (sysctl)",
                "🧠",
                "Kernel Tuning",
                "Tune kernel settings (vm.swappiness, BBR TCP, inotify watches, IPv6) with plain-English value explanations, temporary live changes (sysctl -w), and /etc/sysctl.d/ persistence.",
                self.launch_sysctl,
            ),
            (
                "Advanced Permissions (ACLs & Attr)",
                "🔐",
                "Filesystem Security",
                "Manage POSIX Access Control Lists (setfacl / getfacl) for users and groups, and enforce kernel extended attributes like immutable (+i) via chattr and lsattr.",
                self.launch_permissions,
            ),
            (
                "Bootloader & Kernel Args",
                "🚀",
                "Boot Sequence",
                "Configure kernel boot parameters (quiet, nomodeset, nowatchdog) and timeouts for GRUB (/etc/default/grub) and systemd-boot with safe configuration regeneration.",
                self.launch_bootloader,
            ),
        ]

        for idx, (t, icon, cat, desc, callback) in enumerate(card_data):
            card = LauncherCard(t, icon, cat, desc, callback)
            self.cards.append(card)
            row = idx // 3
            col = idx % 3
            self.grid.addWidget(card, row, col)

        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _filter_cards(self, text: str) -> None:
        needle = text.lower()
        for card in self.cards:
            matches = needle in card.findChildren(QLabel)[1].text().lower() or \
                      needle in card.findChildren(QLabel)[2].text().lower() or \
                      needle in card.findChildren(QLabel)[3].text().lower()
            card.setVisible(matches)

    def launch_fstab(self) -> None:
        win = FstabMainWindow()
        win.show()
        self.windows.append(win)

    def launch_udev(self) -> None:
        win = UdevMainWindow()
        win.show()
        self.windows.append(win)

    def launch_systemd(self) -> None:
        win = SystemdMainWindow()
        win.show()
        self.windows.append(win)

    def launch_usermgmt(self) -> None:
        win = UserMgmtMainWindow()
        win.show()
        self.windows.append(win)

    def launch_sudoers(self) -> None:
        win = SudoersMainWindow()
        win.show()
        self.windows.append(win)

    def launch_journal(self) -> None:
        win = JournalMainWindow()
        win.show()
        self.windows.append(win)

    def launch_sysctl(self) -> None:
        win = SysctlMainWindow()
        win.show()
        self.windows.append(win)

    def launch_permissions(self) -> None:
        win = PermissionsMainWindow()
        win.show()
        self.windows.append(win)

    def launch_bootloader(self) -> None:
        win = BootloaderMainWindow()
        win.show()
        self.windows.append(win)


def main() -> None:
    app = QApplication(sys.argv)
    apply_theme(app)
    launcher = LauncherMainWindow()
    launcher.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
