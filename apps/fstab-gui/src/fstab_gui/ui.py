"""User Interface for Fstab GUI editor."""

import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from linux_gui_core.runner.executor import SafeExecutor
from linux_gui_core.widgets.preview_banner import LivePreviewBanner
from linux_gui_core.widgets.safety_dialog import SafetyExecutionDialog, generate_diff
from linux_gui_core.widgets.tooltips import format_tooltip
from fstab_gui.parser import FstabEntry, FstabParser


ADVANCED_FSTAB_OPTIONS = [
    # systemd Automount & Network
    (
        "x-systemd.automount",
        "systemd On-Demand Automount",
        "Creates a systemd automount unit that mounts the drive automatically when accessed by an application or user, saving boot time.",
        "Recommended for network & USB drives",
    ),
    (
        "x-systemd.idle-timeout=5min",
        "systemd Idle Auto-Unmount",
        "Automatically unmounts the filesystem after 5 minutes of inactivity to save power or safely disconnect network shares.",
        "Safe / Power Saving",
    ),
    (
        "x-systemd.device-timeout=15s",
        "systemd Device Discovery Timeout",
        "Configures how long systemd waits for the block device to show up at boot before timing out (default is 90s).",
        "Safe / Speeds up boot with missing drives",
    ),
    (
        "x-systemd.requires=network-online.target",
        "Wait for Network Online",
        "Ensures network routing and interfaces are fully active before mounting this partition (NFS, SMB, SSHFS).",
        "Recommended for Network Storage",
    ),
    (
        "x-systemd.makefs",
        "Auto-Format If Missing",
        "Instructs systemd to automatically initialize and format the partition if no filesystem signature is detected.",
        "Caution / Formats Empty Disks",
    ),
    (
        "x-systemd.growfs",
        "Auto-Grow Filesystem",
        "Expands the filesystem to fill the underlying partition boundary at mount time.",
        "Safe / Resized Partitions",
    ),
    (
        "_netdev",
        "Network-Dependent Filesystem",
        "Informs mount tools that this filesystem depends on network connectivity.",
        "Recommended for NFS / Samba",
    ),
    (
        "noauto",
        "Do Not Mount At Boot",
        "Prevents the partition from being mounted automatically during system boot or with 'mount -a'.",
        "Safe / Manual Mount Only",
    ),
    # Btrfs / ZFS / Advanced Filesystem
    (
        "compress=zstd",
        "Btrfs Zstandard Compression",
        "Enables high-performance Zstandard transparent compression on Btrfs.",
        "Recommended for Btrfs",
    ),
    (
        "subvol=@home",
        "Btrfs Subvolume Mount",
        "Mounts a specific Btrfs subvolume instead of the top-level root.",
        "Standard Btrfs",
    ),
    (
        "nodatacow",
        "Disable Copy-On-Write (NoCoW)",
        "Disables Copy-on-Write for Btrfs. Useful for database tables and virtual machine images to prevent fragmentation.",
        "Caution / Specialized Workloads",
    ),
    # Ownership & Permissions (FAT/NTFS)
    (
        "uid=1000,gid=1000",
        "Set Default User/Group Owner",
        "Sets the owning user and group ID for filesystems that do not support Linux file ownership (FAT32, exFAT, NTFS).",
        "Recommended for USB Flash Drives",
    ),
    (
        "umask=022",
        "Default Permission Mask (755 / 644)",
        "Sets file permission mask (rwxr-xr-x) for filesystems lacking POSIX permissions.",
        "Standard FAT/NTFS",
    ),
    (
        "windows_names",
        "Enforce Windows Filename Compatibility",
        "Prevents creation of filenames containing characters prohibited on Windows (: * ? \" < > |).",
        "Safe for Dual-Boot",
    ),
    # Other
    (
        "x-gvfs-show",
        "Show in File Manager",
        "Allows the filesystem to be visible in file managers like Nautilus, Thunar, and Dolphin.",
        "User Interface",
    )
]


class AdvancedFstabOptionDialog(QDialog):
    """Searchable dialog to select or enter advanced / systemd fstab options."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search & Add Advanced / systemd Mount Option")
        self.resize(680, 480)
        self.selected_option: str = ""

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search Options:"))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search 'automount', 'network', 'timeout', 'compress', 'btrfs'...")
        self.txt_search.textChanged.connect(self._filter_list)
        search_layout.addWidget(self.txt_search)
        layout.addLayout(search_layout)

        # Options list
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_preset_double_clicked)
        self._populate_list()
        layout.addWidget(self.list_widget)

        # Custom entry
        custom_box = QGroupBox("Or Enter Custom Mount Option")
        c_layout = QHBoxLayout(custom_box)
        self.txt_custom = QLineEdit()
        self.txt_custom.setPlaceholderText("e.g. x-systemd.automount or subvol=@var or umask=077")
        c_layout.addWidget(self.txt_custom)
        layout.addWidget(custom_box)

        # Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self._accept_selection)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _populate_list(self) -> None:
        self.list_widget.clear()
        for opt_str, title, desc, badge in ADVANCED_FSTAB_OPTIONS:
            item = QListWidgetItem(f"{opt_str}: {title}\n    {desc} ({badge})")
            item.setData(Qt.ItemDataRole.UserRole, opt_str)
            self.list_widget.addItem(item)

    def _filter_list(self, text: str) -> None:
        needle = text.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(needle not in item.text().lower())

    def _on_preset_double_clicked(self, item: QListWidgetItem) -> None:
        self.selected_option = item.data(Qt.ItemDataRole.UserRole)
        self.accept()

    def _accept_selection(self) -> None:
        custom = self.txt_custom.text().strip()
        if custom:
            self.selected_option = custom
            self.accept()
            return

        cur = self.list_widget.currentItem()
        if cur:
            self.selected_option = cur.data(Qt.ItemDataRole.UserRole)
            self.accept()
        else:
            QMessageBox.warning(self, "No Selection", "Please choose an option from the list or enter a custom one.")


class FstabMainWindow(QMainWindow):
    """Main application window for inspecting and modifying /etc/fstab entries."""

    FSTAB_PATH = "/etc/fstab"

    COMMON_OPTIONS = [
        ("defaults", "Use default mount options (rw, suid, dev, exec, auto, nouser, async)", "Safe", "Standard for root & root-managed partitions"),
        ("noatime", "Do not update inode access times on the filesystem. Can improve performance.", "Safe", "noatime on SSD drives reduces writes"),
        ("ro", "Mount filesystem in read-only mode. Prevents any modifications.", "Hardening", "ro for backup storage or immutable mounts"),
        ("nosuid", "Do not allow set-user-identifier or set-group-identifier bits to take effect. Prevents privilege escalation.", "Hardening", "nosuid on /tmp, /home, or USB storage"),
        ("nodev", "Do not interpret character or block special devices on the filesystem. Prevents unauthorized device node creation.", "Hardening", "nodev on user-accessible drives"),
        ("noexec", "Do not allow direct execution of any binaries on the mounted filesystem.", "Hardening", "noexec on /tmp or download partitions"),
        ("nofail", "Do not report errors or halt boot if this drive is not plugged in.", "Recommended for external drives", "nofail on external USB drives & secondary storage"),
        ("_netdev", "The filesystem requires network access (e.g. NFS, CIFS). Systemd waits until network is up before mounting.", "Recommended for network drives", "_netdev on NFS / Samba shares"),
        ("user", "Allow ordinary (non-root) users to mount and unmount this filesystem.", "Caution", "user for external flash drives"),
    ]

    def __init__(self, fstab_path: str = "/etc/fstab"):
        super().__init__()
        self.fstab_path = fstab_path
        self.setWindowTitle(f"fstab Editor - {self.fstab_path}")
        self.resize(1180, 820)
        self.setMinimumSize(960, 680)

        self.entries: list[FstabEntry] = []
        self.original_raw: str = ""
        self._is_updating_ui: bool = False

        self._init_ui()
        self.reload_fstab()

    def _init_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Top Live Preview Banner
        self.preview_banner = LivePreviewBanner(
            title="/etc/fstab entry preview",
            subtitle="The line below updates as you toggle options. Hover over options for safety & command tooltips.",
        )
        self.preview_banner.diffRequested.connect(self._inspect_file_diff)
        main_layout.addWidget(self.preview_banner)

        # File header with Package Ownership Badge
        header_bar = QHBoxLayout()
        header_bar.addWidget(QLabel(f"Target File: <code>{self.fstab_path}</code>"))
        header_bar.addStretch()
        main_layout.addLayout(header_bar)

        # 2. Splitter: Top = Entries Table, Bottom = Active Entry Form & Checkboxes
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Table of entries
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Device / UUID",
            "Mount Point",
            "Filesystem",
            "Options",
            "Dump",
            "Pass",
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        splitter.addWidget(self.table)

        # Bottom Form Container in ScrollArea to prevent clipping
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(4, 6, 4, 6)
        form_layout.setSpacing(10)

        # Entry Parameters Box
        params_group = QGroupBox("Selected Entry Properties")
        params_grid = QGridLayout(params_group)
        params_grid.setSpacing(8)

        # Device / Spec
        params_grid.addWidget(QLabel("Device / UUID / LABEL:"), 0, 0)
        self.txt_spec = QLineEdit()
        self.txt_spec.setPlaceholderText("e.g. UUID=3a7b-..., LABEL=Data, /dev/sdb1")
        self.txt_spec.setToolTip(format_tooltip(
            "Filesystem Specification",
            "UUID=... or LABEL=... or /dev/...",
            "Identifies the disk partition. Using UUID is strongly recommended because device names like /dev/sda can change across reboots.<br><br><b>Cannot be blank</b>. Must identify a partition.",
            "Recommended: UUID",
            "UUID=1234-ABCD",
        ))
        self.txt_spec.textChanged.connect(self._on_entry_modified)
        params_grid.addWidget(self.txt_spec, 0, 1)

        # Mount point
        params_grid.addWidget(QLabel("Mount Point:"), 0, 2)
        self.txt_mount = QLineEdit()
        self.txt_mount.setPlaceholderText("e.g. /, /home, /mnt/storage")
        self.txt_mount.setToolTip(format_tooltip(
            "Mount Point",
            "/path/to/folder",
            "The directory in the root hierarchy where the filesystem is made accessible (or 'none' for swap).<br><br><b>Cannot be blank</b>.",
            "Required directory",
            "/mnt/data",
        ))
        self.txt_mount.textChanged.connect(self._on_entry_modified)
        params_grid.addWidget(self.txt_mount, 0, 3)

        # Filesystem Type
        params_grid.addWidget(QLabel("Filesystem Type:"), 1, 0)
        self.cmb_fstype = QComboBox()
        self.cmb_fstype.setEditable(True)
        self.cmb_fstype.addItems(["ext4", "btrfs", "xfs", "vfat", "ntfs3", "exfat", "swap", "nfs", "auto"])
        self.cmb_fstype.currentTextChanged.connect(self._on_entry_modified)
        params_grid.addWidget(self.cmb_fstype, 1, 1)

        # Dump & Pass
        spin_layout = QHBoxLayout()
        spin_layout.addWidget(QLabel("Dump:"))
        self.spn_dump = QSpinBox()
        self.spn_dump.setRange(0, 1)
        self.spn_dump.setToolTip(format_tooltip("Dump Flag", "0 or 1", "Used by dump utility to backup filesystem. Rarely used on modern Linux; defaults to 0.<br><br><b>Cannot be blank</b>"))
        self.spn_dump.valueChanged.connect(self._on_entry_modified)
        spin_layout.addWidget(self.spn_dump)

        spin_layout.addWidget(QLabel("Pass:"))
        self.spn_pass = QSpinBox()
        self.spn_pass.setRange(0, 2)
        self.spn_pass.setToolTip(format_tooltip(
            "Fsck Pass Order",
            "0 (skip), 1 (root partition), 2 (other partitions)",
            "Determines the order in which filesystem checks are done at reboot time.<br><br><b>Cannot be blank</b>.",
            "Safer to use 1 for root (/), 2 for other local drives, 0 for swap/network. Use 0 for xfs and btrfs mounts.",
        ))
        self.spn_pass.valueChanged.connect(self._on_entry_modified)
        spin_layout.addWidget(self.spn_pass)

        params_grid.addLayout(spin_layout, 1, 2, 1, 2)
        form_layout.addWidget(params_group)

        # Checkboxes for Common Mount Options
        opts_group = QGroupBox("Common Mount Options (Click any to toggle in real time)")
        opts_grid = QGridLayout(opts_group)
        opts_grid.setSpacing(10)

        self.option_checkboxes: dict[str, QCheckBox] = {}
        for idx, (opt, desc, impact, example) in enumerate(self.COMMON_OPTIONS):
            chk = QCheckBox(opt)
            chk.setToolTip(format_tooltip(f"Mount Option: {opt}", opt, desc, impact, example))
            chk.toggled.connect(self._on_entry_modified)
            self.option_checkboxes[opt] = chk
            row = idx // 5
            col = idx % 5
            opts_grid.addWidget(chk, row, col)

        form_layout.addWidget(opts_group)

        # Advanced / Systemd Options Group (Search Catalog)
        adv_group = QGroupBox("Advanced Mount Options (e.g. Automount, Network Dependencies, Timeouts)")
        adv_layout = QVBoxLayout(adv_group)

        adv_bar = QHBoxLayout()
        self.lbl_adv_count = QLabel("Active Advanced / Custom Options:")
        self.lbl_adv_count.setStyleSheet("color: #89b4fa; font-weight: bold;")
        adv_bar.addWidget(self.lbl_adv_count)
        adv_bar.addStretch()

        btn_search_opts = QPushButton("Add Advanced Option")
        btn_search_opts.setToolTip("Search a catalog of mount options including systemd automount, network targets, idle timeouts, and Btrfs subvolumes.")
        btn_search_opts.clicked.connect(self._open_advanced_options_dialog)
        adv_bar.addWidget(btn_search_opts)
        adv_layout.addLayout(adv_bar)

        self.tbl_adv = QTableWidget(0, 2)
        self.tbl_adv.setHorizontalHeaderLabels(["Option Directive", "Action"])
        self.tbl_adv.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_adv.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tbl_adv.setColumnWidth(1, 100)
        self.tbl_adv.setFixedHeight(110)
        adv_layout.addWidget(self.tbl_adv)

        form_layout.addWidget(adv_group)

        scroll.setWidget(form_container)
        splitter.addWidget(scroll)
        main_layout.addWidget(splitter)

        # Bottom Action Bar
        action_layout = QHBoxLayout()
        self.btn_new = QPushButton("➕ Add New Entry")
        self.btn_new.clicked.connect(self._add_new_entry)
        action_layout.addWidget(self.btn_new)

        self.btn_delete = QPushButton("🗑️ Remove Selected")
        self.btn_delete.clicked.connect(self._remove_selected_entry)
        action_layout.addWidget(self.btn_delete)

        self.btn_test = QPushButton("🧪 Dry Run (mount -fa)")
        self.btn_test.setToolTip("Runs 'mount -fa' (fake mount) to validate the fstab syntax without actually mounting filesystems.")
        self.btn_test.clicked.connect(self._test_dry_run)
        action_layout.addWidget(self.btn_test)

        action_layout.addStretch()

        self.btn_apply = QPushButton("💾 Apply && Save to /etc/fstab")
        self.btn_apply.setObjectName("primaryBtn")
        self.btn_apply.setToolTip("Inspects diff, creates automatic backup, and writes changes with elevated privileges.")
        self.btn_apply.clicked.connect(self._apply_changes)
        action_layout.addWidget(self.btn_apply)

        main_layout.addLayout(action_layout)

    def reload_fstab(self) -> None:
        """Reads entries from disk."""
        if os.path.exists(self.fstab_path):
            with open(self.fstab_path, "r", encoding="utf-8") as f:
                self.original_raw = f.read()
        else:
            self.original_raw = ""

        self.entries = FstabParser.parse_file(self.fstab_path)
        self._populate_table()

    def _populate_table(self) -> None:
        self._is_updating_ui = True
        self.table.setRowCount(0)
        row = 0
        for entry in self.entries:
            if entry.raw_comment:
                continue
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(entry.fs_spec))
            self.table.setItem(row, 1, QTableWidgetItem(entry.mount_point))
            self.table.setItem(row, 2, QTableWidgetItem(entry.vfstype))
            self.table.setItem(row, 3, QTableWidgetItem(",".join(entry.options)))
            self.table.setItem(row, 4, QTableWidgetItem(str(entry.dump)))
            self.table.setItem(row, 5, QTableWidgetItem(str(entry.passno)))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, entry)
            row += 1

        self._is_updating_ui = False
        if self.table.rowCount() > 0:
            self.table.selectRow(0)

    def _on_table_selection_changed(self) -> None:
        if self._is_updating_ui:
            return
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        entry: FstabEntry = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self._load_entry_to_form(entry)

    def _load_entry_to_form(self, entry: FstabEntry) -> None:
        self._is_updating_ui = True
        self.txt_spec.setText(entry.fs_spec)
        self.txt_mount.setText(entry.mount_point)
        self.cmb_fstype.setCurrentText(entry.vfstype)
        self.spn_dump.setValue(entry.dump)
        self.spn_pass.setValue(entry.passno)

        opts_set = set(entry.options)
        for opt_name, chk in self.option_checkboxes.items():
            chk.setChecked(opt_name in opts_set)

        self._populate_advanced_options_table(entry)
        self._is_updating_ui = False
        self.preview_banner.set_text(entry.to_line())

    def _populate_advanced_options_table(self, entry: FstabEntry) -> None:
        common_keys = set(self.option_checkboxes.keys())
        extra_opts = [o for o in entry.options if o not in common_keys]

        self.tbl_adv.setRowCount(0)
        for idx, opt in enumerate(extra_opts):
            self.tbl_adv.insertRow(idx)
            self.tbl_adv.setItem(idx, 0, QTableWidgetItem(opt))
            btn_del = QPushButton("❌ Remove")
            btn_del.clicked.connect(lambda _, o=opt: self._remove_advanced_option(o))
            self.tbl_adv.setCellWidget(idx, 1, btn_del)

    def _remove_advanced_option(self, option_to_remove: str) -> None:
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        entry: FstabEntry = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if option_to_remove in entry.options:
            entry.options.remove(option_to_remove)
            self._load_entry_to_form(entry)
            self._on_entry_modified()

    def _open_advanced_options_dialog(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "No Entry Selected", "Please select an entry in the fstab table first.")
            return
        row = selected[0].row()
        entry: FstabEntry = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        dlg = AdvancedFstabOptionDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_option:
            new_opt = dlg.selected_option.strip()
            if new_opt and new_opt not in entry.options:
                if "defaults" in entry.options:
                    entry.options.remove("defaults")
                entry.options.append(new_opt)
                self._load_entry_to_form(entry)
                self._on_entry_modified()

    def _on_entry_modified(self) -> None:
        if self._is_updating_ui:
            return
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        entry: FstabEntry = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        entry.fs_spec = self.txt_spec.text().strip()
        entry.mount_point = self.txt_mount.text().strip()
        entry.vfstype = self.cmb_fstype.currentText().strip()
        entry.dump = self.spn_dump.value()
        entry.passno = self.spn_pass.value()

        common_keys = set(self.option_checkboxes.keys())
        preserved_extras = [o for o in entry.options if o not in common_keys]
        selected_common = [name for name, chk in self.option_checkboxes.items() if chk.isChecked()]
        all_options = selected_common + preserved_extras

        if not all_options:
            all_options = ["defaults"]
        entry.options = all_options

        self._is_updating_ui = True
        self.table.item(row, 0).setText(entry.fs_spec)
        self.table.item(row, 1).setText(entry.mount_point)
        self.table.item(row, 2).setText(entry.vfstype)
        self.table.item(row, 3).setText(",".join(entry.options))
        self.table.item(row, 4).setText(str(entry.dump))
        self.table.item(row, 5).setText(str(entry.passno))
        self._is_updating_ui = False

        self.preview_banner.set_text(entry.to_line())

    def _add_new_entry(self) -> None:
        new_entry = FstabEntry(
            fs_spec="UUID=NEW-DEVICE-UUID",
            mount_point="/mnt/new_drive",
            vfstype="ext4",
            options=["defaults", "noatime"],
            dump=0,
            passno=2,
        )
        self.entries.append(new_entry)
        self._populate_table()
        self.table.selectRow(self.table.rowCount() - 1)

    def _remove_selected_entry(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        entry = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        confirm = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove the mount entry for:\n\n{entry.mount_point} ({entry.fs_spec})?",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.entries.remove(entry)
            self._populate_table()

    def _inspect_file_diff(self) -> None:
        modified_raw = FstabParser.serialize_entries(self.entries)
        diff = generate_diff(self.original_raw, modified_raw, "fstab")
        if not diff.strip():
            QMessageBox.information(self, "No Changes", "No changes detected compared to the current file.")
            return

        notes = [
            "Automatic backup will be created before saving.",
            "Review that the root (/) and /boot entries are intact.",
        ]

        dlg = SafetyExecutionDialog(
            title="Inspect /etc/fstab Diff",
            target_path_or_command=self.fstab_path,
            diff_text=diff,
            safety_notes=notes,
            parent=self,
        )
        dlg.exec()

    def _test_dry_run(self) -> None:
        res = SafeExecutor.run_command(["mount", "-fa"])
        if res.success:
            QMessageBox.information(self, "Dry-Run Check Passed", "Command 'mount -fa' reported no syntax or mounting errors.")
        else:
            QMessageBox.warning(self, "Dry-Run Warning", f"mount -fa reported:\n{res.stderr or res.stdout}")

    def _apply_changes(self) -> None:
        modified_raw = FstabParser.serialize_entries(self.entries)
        diff = generate_diff(self.original_raw, modified_raw, "fstab")

        notes = [
            "Timestamped backup will be created in /etc/fstab.bak.<timestamp>",
            "Uses elevated privileges via pkexec.",
        ]

        dlg = SafetyExecutionDialog(
            title="Apply /etc/fstab Modifications",
            target_path_or_command=self.fstab_path,
            diff_text=diff if diff.strip() else "# No differences detected",
            safety_notes=notes,
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = SafeExecutor.safe_write_system_file(self.fstab_path, modified_raw)
            if res.success:
                QMessageBox.information(
                    self,
                    "Success",
                    f"/etc/fstab updated successfully!\nBackup: {res.backup_file}",
                )
                self.reload_fstab()
            else:
                QMessageBox.critical(self, "Error Applying Changes", f"Failed:\n{res.stderr}")
