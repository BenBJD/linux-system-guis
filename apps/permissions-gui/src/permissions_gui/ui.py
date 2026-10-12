"""User interface for Advanced Linux File Permissions (ACLs & Attributes)."""

import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from linux_gui_core.widgets.preview_banner import LivePreviewBanner
from linux_gui_core.widgets.safety_dialog import SafetyExecutionDialog
from linux_gui_core.widgets.tooltips import format_tooltip
from permissions_gui.backend import ACLEntry, PermissionsBackend


class PermissionsMainWindow(QMainWindow):
    """Main application window for managing POSIX ACLs and Linux extended attributes."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advanced File Permissions (ACLs & Attributes)")
        self.resize(1180, 820)
        self.setMinimumSize(960, 680)

        self.current_path: str = os.path.expanduser("~")
        self.acl_entries: list[ACLEntry] = []
        self._is_updating_ui: bool = False

        self._init_ui()
        self._inspect_path()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Top Live Preview Banner
        self.preview_banner = LivePreviewBanner(
            title="EXACT PERMISSION COMMAND PREVIEW",
            subtitle="Modifying ACL entries or attributes below dynamically constructs the exact setfacl or chattr command.",
        )
        layout.addWidget(self.preview_banner)

        # 2. Target File/Folder Selection Bar
        path_bar = QHBoxLayout()
        path_bar.addWidget(QLabel("Target Path:"))
        self.txt_path = QLineEdit(self.current_path)
        self.txt_path.returnPressed.connect(self._on_path_entered)
        path_bar.addWidget(self.txt_path)

        btn_browse_file = QPushButton("📄 Select File...")
        btn_browse_file.clicked.connect(self._browse_file)
        path_bar.addWidget(btn_browse_file)

        btn_browse_dir = QPushButton("📁 Select Folder...")
        btn_browse_dir.clicked.connect(self._browse_dir)
        path_bar.addWidget(btn_browse_dir)

        layout.addLayout(path_bar)

        # Basic Stats Pill
        self.lbl_stats = QLabel("Checking permissions...")
        self.lbl_stats.setStyleSheet(
            "background-color: #181825; border: 1px solid #313244; border-radius: 6px; padding: 6px 10px; color: #89b4fa; font-family: monospace;"
        )
        layout.addWidget(self.lbl_stats)

        # 3. Main Tabs: ACLs vs Attributes
        tabs = QTabWidget()

        # Tab 1: Access Control Lists (ACLs)
        tab_acl = QWidget()
        acl_layout = QVBoxLayout(tab_acl)
        acl_layout.setContentsMargins(8, 8, 8, 8)
        acl_layout.setSpacing(10)

        acl_splitter = QSplitter(Qt.Orientation.Vertical)

        # Current ACL table
        self.tbl_acls = QTableWidget(0, 4)
        self.tbl_acls.setHorizontalHeaderLabels([
            "Principal Type",
            "Target Name",
            "Permissions (rwx)",
            "Default Inheritance?",
        ])
        self.tbl_acls.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tbl_acls.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.tbl_acls.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tbl_acls.setColumnWidth(0, 160)
        self.tbl_acls.setColumnWidth(1, 220)
        self.tbl_acls.setColumnWidth(2, 160)
        self.tbl_acls.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        acl_splitter.addWidget(self.tbl_acls)

        # Form to grant/modify ACL
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        acl_form_container = QWidget()
        form_layout = QVBoxLayout(acl_form_container)
        form_layout.setContentsMargins(4, 6, 4, 6)
        form_layout.setSpacing(10)

        grant_box = QGroupBox("Grant or Modify Extended Access Control Entry (setfacl -m)")
        grant_grid = QGridLayout(grant_box)
        grant_grid.setSpacing(8)

        # Principal type (user vs group)
        self.rb_user = QRadioButton("User (u:)")
        self.rb_user.setChecked(True)
        self.rb_group = QRadioButton("Group (g:)")
        self.rb_user.toggled.connect(self._update_acl_preview)
        self.rb_group.toggled.connect(self._update_acl_preview)
        grant_grid.addWidget(self.rb_user, 0, 0)
        grant_grid.addWidget(self.rb_group, 0, 1)

        grant_grid.addWidget(QLabel("User or Group Name:"), 0, 2)
        self.txt_principal = QLineEdit("alice")
        self.txt_principal.setPlaceholderText("e.g. alice, developers, docker")
        self.txt_principal.setToolTip(format_tooltip(
            "ACL Recipient",
            "u:username or g:groupname",
            "The specific user account or group granted permissions beyond the base owner.",
            "Required",
        ))
        self.txt_principal.textChanged.connect(self._update_acl_preview)
        grant_grid.addWidget(self.txt_principal, 0, 3)

        # Permission checkboxes
        perm_bar = QHBoxLayout()
        perm_bar.addWidget(QLabel("Permissions:"))
        self.chk_read = QCheckBox("Read (r)")
        self.chk_read.setChecked(True)
        self.chk_read.toggled.connect(self._update_acl_preview)
        perm_bar.addWidget(self.chk_read)

        self.chk_write = QCheckBox("Write (w)")
        self.chk_write.setChecked(True)
        self.chk_write.toggled.connect(self._update_acl_preview)
        perm_bar.addWidget(self.chk_write)

        self.chk_exec = QCheckBox("Execute (x)")
        self.chk_exec.toggled.connect(self._update_acl_preview)
        perm_bar.addWidget(self.chk_exec)
        perm_bar.addStretch()
        grant_grid.addLayout(perm_bar, 1, 0, 1, 2)

        # Flags: default (-d) and recursive (-R)
        flags_bar = QHBoxLayout()
        self.chk_default = QCheckBox("Default ACL (-d) - Newly created files inherit this")
        self.chk_default.setToolTip(format_tooltip(
            "Inherited Default ACL",
            "setfacl -d -m ...",
            "Only applicable to directories. Files and subfolders created inside will automatically inherit this access entry.",
            "Recommended for shared folders",
        ))
        self.chk_default.toggled.connect(self._update_acl_preview)
        flags_bar.addWidget(self.chk_default)

        self.chk_recursive = QCheckBox("Recursive (-R)")
        self.chk_recursive.setToolTip(format_tooltip("Recursive Application", "-R", "Applies permissions recursively to all subdirectories."))
        self.chk_recursive.toggled.connect(self._update_acl_preview)
        flags_bar.addWidget(self.chk_recursive)
        flags_bar.addStretch()
        grant_grid.addLayout(flags_bar, 1, 2, 1, 2)

        form_layout.addWidget(grant_box)
        scroll.setWidget(acl_form_container)
        acl_splitter.addWidget(scroll)
        acl_layout.addWidget(acl_splitter)

        # Action Buttons
        acl_action_bar = QHBoxLayout()
        btn_apply_acl = QPushButton("➕ Grant / Apply ACL Entry")
        btn_apply_acl.setObjectName("primaryBtn")
        btn_apply_acl.clicked.connect(self._apply_acl_entry)
        acl_action_bar.addWidget(btn_apply_acl)

        btn_rm_acl = QPushButton("🗑️ Remove Selected ACL (-x)")
        btn_rm_acl.setToolTip("Deletes the selected extended ACL entry using 'setfacl -x'.")
        btn_rm_acl.clicked.connect(self._remove_selected_acl)
        acl_action_bar.addWidget(btn_rm_acl)

        acl_action_bar.addStretch()

        btn_strip_all = QPushButton("🧹 Strip All Extended ACLs (-b)")
        btn_strip_all.setToolTip("Removes all extended ACL entries, restoring standard POSIX permissions.")
        btn_strip_all.clicked.connect(self._strip_all_acls)
        acl_action_bar.addWidget(btn_strip_all)

        acl_layout.addLayout(acl_action_bar)
        tabs.addTab(tab_acl, "👥 Access Control Lists (getfacl / setfacl)")

        # Tab 2: Linux Extended File Attributes (chattr / lsattr)
        tab_attr = QWidget()
        attr_layout = QVBoxLayout(tab_attr)
        attr_layout.setContentsMargins(16, 16, 16, 16)
        attr_layout.setSpacing(14)

        status_attr_box = QGroupBox("Current Linux File Attributes (lsattr)")
        status_attr_layout = QVBoxLayout(status_attr_box)
        self.lbl_attr_raw = QLabel("lsattr output: (loading)")
        self.lbl_attr_raw.setStyleSheet("font-size: 15px; font-weight: bold; color: #89b4fa; font-family: monospace; padding: 6px;")
        status_attr_layout.addWidget(self.lbl_attr_raw)

        lbl_attr_expl = QLabel(
            "Extended attributes are low-level filesystem flags enforced directly by the Linux kernel "
            "(ext4, btrfs, xfs). They can make files completely immutable—preventing accidental deletion "
            "even by the root user!"
        )
        lbl_attr_expl.setWordWrap(True)
        lbl_attr_expl.setStyleSheet("color: #a6adc8; font-size: 12px;")
        status_attr_layout.addWidget(lbl_attr_expl)
        attr_layout.addWidget(status_attr_box)

        # Attributes Checkbox Form
        flags_group = QGroupBox("Configure Kernel Attributes (Click any to toggle)")
        flags_grid = QGridLayout(flags_group)
        flags_grid.setSpacing(12)

        self.chk_attr_i = QCheckBox("Immutable (+i) - Cannot be modified, deleted, renamed, or linked, even by root!")
        self.chk_attr_i.setToolTip(format_tooltip(
            "Immutable Flag",
            "sudo chattr +i <file>",
            "Locks the file completely against all modifications, renames, and deletions. Even root cannot delete an immutable file without removing the +i flag first.",
            "Ultimate Protection against deletion",
        ))
        flags_grid.addWidget(self.chk_attr_i, 0, 0)

        self.chk_attr_a = QCheckBox("Append-Only (+a) - Can only be opened in append mode (Ideal for audit logs)")
        self.chk_attr_a.setToolTip(format_tooltip(
            "Append-Only Flag",
            "sudo chattr +a <file>",
            "Processes can only append data to the end of the file; existing content cannot be overwritten or deleted.",
            "Recommended for Security Logs",
        ))
        flags_grid.addWidget(self.chk_attr_a, 1, 0)

        self.chk_attr_d = QCheckBox("No-Dump (+d) - Excluded from backup archives created by dump utility")
        self.chk_attr_d.setToolTip(format_tooltip("No-Dump Flag", "chattr +d", "Prevents file from being backed up by dump utility."))
        flags_grid.addWidget(self.chk_attr_d, 2, 0)

        self.chk_attr_c = QCheckBox("Compressed (+c) - Transparent filesystem compression on disk")
        self.chk_attr_c.setToolTip(format_tooltip("Compressed Flag", "chattr +c", "Requests kernel transparent compression on supported filesystems."))
        flags_grid.addWidget(self.chk_attr_c, 3, 0)

        self.chk_attr_s = QCheckBox("Secure Deletion (+s) - Zeroes out disk blocks upon file deletion")
        self.chk_attr_s.setToolTip(format_tooltip("Secure Deletion Flag", "chattr +s", "Forces kernel to zero out blocks when unlinking."))
        flags_grid.addWidget(self.chk_attr_s, 4, 0)

        for chk in (self.chk_attr_i, self.chk_attr_a, self.chk_attr_d, self.chk_attr_c, self.chk_attr_s):
            chk.toggled.connect(self._update_attr_preview)

        attr_layout.addWidget(flags_group)

        attr_btn_bar = QHBoxLayout()
        attr_btn_bar.addStretch()
        btn_apply_attr = QPushButton("💾 Apply Kernel Attributes (sudo chattr)")
        btn_apply_attr.setObjectName("primaryBtn")
        btn_apply_attr.clicked.connect(self._apply_attributes)
        attr_btn_bar.addWidget(btn_apply_attr)
        attr_layout.addLayout(attr_btn_bar)

        attr_layout.addStretch()
        tabs.addTab(tab_attr, "🔒 File Attributes (chattr / lsattr)")

        layout.addWidget(tabs)

    def _browse_file(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Select Target File", self.current_path)
        if p:
            self.txt_path.setText(p)
            self._on_path_entered()

    def _browse_dir(self) -> None:
        p = QFileDialog.getExistingDirectory(self, "Select Target Folder", self.current_path)
        if p:
            self.txt_path.setText(p)
            self._on_path_entered()

    def _on_path_entered(self) -> None:
        p = self.txt_path.text().strip()
        if os.path.exists(p):
            self.current_path = p
            self._inspect_path()
        else:
            QMessageBox.warning(self, "Not Found", f"Path does not exist:\n{p}")

    def _inspect_path(self) -> None:
        p = self.current_path
        stat = PermissionsBackend.get_basic_stat(p)
        if stat:
            t_str = "📁 Directory" if stat["is_dir"] else "📄 File"
            self.lbl_stats.setText(
                f"Target: <b>{p}</b> &nbsp;|&nbsp; Type: {t_str} &nbsp;|&nbsp; "
                f"Mode: <b>0{stat['mode']}</b> &nbsp;|&nbsp; "
                f"Owner: <b>{stat['owner']}</b> &nbsp;|&nbsp; Group: <b>{stat['group']}</b>"
            )
            self.chk_default.setEnabled(stat["is_dir"])
            if not stat["is_dir"]:
                self.chk_default.setChecked(False)

        # Inspect ACLs
        self.acl_entries = PermissionsBackend.parse_acls(p)
        self._populate_acl_table()

        # Inspect Attributes
        attr_str = PermissionsBackend.get_file_attributes(p)
        self.lbl_attr_raw.setText(f"lsattr: {attr_str or '----'}")

        self._is_updating_ui = True
        self.chk_attr_i.setChecked("i" in attr_str)
        self.chk_attr_a.setChecked("a" in attr_str)
        self.chk_attr_d.setChecked("d" in attr_str)
        self.chk_attr_c.setChecked("c" in attr_str)
        self.chk_attr_s.setChecked("s" in attr_str)
        self._is_updating_ui = False

        self._update_acl_preview()

    def _populate_acl_table(self) -> None:
        self.tbl_acls.setRowCount(0)
        for row, entry in enumerate(self.acl_entries):
            self.tbl_acls.insertRow(row)
            self.tbl_acls.setItem(row, 0, QTableWidgetItem(entry.principal_type))
            self.tbl_acls.setItem(row, 1, QTableWidgetItem(entry.principal_name))
            self.tbl_acls.setItem(row, 2, QTableWidgetItem(entry.permissions))
            def_str = "Yes (Default Inherited)" if entry.is_default else "Direct"
            self.tbl_acls.setItem(row, 3, QTableWidgetItem(def_str))
            self.tbl_acls.item(row, 0).setData(Qt.ItemDataRole.UserRole, entry)

    def _update_acl_preview(self) -> None:
        p_type = "u" if self.rb_user.isChecked() else "g"
        name = self.txt_principal.text().strip() or "username"
        perms = ("r" if self.chk_read.isChecked() else "-") + \
                ("w" if self.chk_write.isChecked() else "-") + \
                ("x" if self.chk_exec.isChecked() else "-")
        is_def = self.chk_default.isChecked()
        rec = self.chk_recursive.isChecked()

        cmd = PermissionsBackend.build_setfacl_cmd(self.current_path, p_type, name, perms, is_def, rec)
        self.preview_banner.set_text(" ".join(cmd))

    def _update_attr_preview(self) -> None:
        if self._is_updating_ui:
            return
        flags = []
        if self.chk_attr_i.isChecked():
            flags.append("+i")
        if self.chk_attr_a.isChecked():
            flags.append("+a")
        if self.chk_attr_d.isChecked():
            flags.append("+d")
        if self.chk_attr_c.isChecked():
            flags.append("+c")
        if self.chk_attr_s.isChecked():
            flags.append("+s")
        flag_str = "".join(flags) if flags else "none"
        self.preview_banner.set_text(f"sudo chattr {flag_str} {self.current_path}")

    def _apply_acl_entry(self) -> None:
        name = self.txt_principal.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing Name", "Please specify a target user or group name.")
            return

        p_type = "u" if self.rb_user.isChecked() else "g"
        perms = ("r" if self.chk_read.isChecked() else "-") + \
                ("w" if self.chk_write.isChecked() else "-") + \
                ("x" if self.chk_exec.isChecked() else "-")
        is_def = self.chk_default.isChecked()
        rec = self.chk_recursive.isChecked()

        cmd_list = PermissionsBackend.build_setfacl_cmd(self.current_path, p_type, name, perms, is_def, rec)
        cmd_str = " ".join(cmd_list)

        dlg = SafetyExecutionDialog(
            title="Apply Access Control List (ACL)",
            target_path_or_command=cmd_str,
            safety_notes=[
                f"Grants extended permissions '{perms}' to {p_type}:{name}",
                "Uses elevated privileges via pkexec.",
            ],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = PermissionsBackend.apply_setfacl(self.current_path, p_type, name, perms, is_def, rec)
            if res.success:
                QMessageBox.information(self, "ACL Applied", f"Permission successfully granted!\n\n{cmd_str}")
                self._inspect_path()
            else:
                QMessageBox.critical(self, "Error", f"Failed:\n{res.stderr or res.stdout}")

    def _remove_selected_acl(self) -> None:
        selected = self.tbl_acls.selectedItems()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select an ACL entry from the table first.")
            return
        row = selected[0].row()
        entry: ACLEntry = self.tbl_acls.item(row, 0).data(Qt.ItemDataRole.UserRole)

        confirm = QMessageBox.question(
            self,
            "Remove ACL Entry",
            f"Remove ACL entry for {entry.principal_type}:{entry.principal_name}?",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            res = PermissionsBackend.remove_acl_entry(self.current_path, entry)
            if res.success:
                self._inspect_path()
            else:
                QMessageBox.critical(self, "Failed", f"Error:\n{res.stderr}")

    def _strip_all_acls(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Strip All ACLs",
            f"Remove ALL extended ACL entries from {self.current_path}?",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            res = PermissionsBackend.remove_all_acls(self.current_path)
            if res.success:
                self._inspect_path()
            else:
                QMessageBox.critical(self, "Failed", f"Error:\n{res.stderr}")

    def _apply_attributes(self) -> None:
        # Build flag string
        cur_attr = PermissionsBackend.get_file_attributes(self.current_path)
        plus = []
        minus = []

        mapping = [
            ("i", self.chk_attr_i.isChecked()),
            ("a", self.chk_attr_a.isChecked()),
            ("d", self.chk_attr_d.isChecked()),
            ("c", self.chk_attr_c.isChecked()),
            ("s", self.chk_attr_s.isChecked()),
        ]

        for flag, is_set in mapping:
            has_flag = flag in cur_attr
            if is_set and not has_flag:
                plus.append(flag)
            elif not is_set and has_flag:
                minus.append(flag)

        parts = []
        if plus:
            parts.append(f"+{''.join(plus)}")
        if minus:
            parts.append(f"-{''.join(minus)}")

        if not parts:
            QMessageBox.information(self, "No Changes", "Attributes match current state; no changes to apply.")
            return

        cmd_flag = " ".join(parts)
        cmd_str = f"sudo chattr {cmd_flag} {self.current_path}"

        dlg = SafetyExecutionDialog(
            title="Apply File Attributes",
            target_path_or_command=cmd_str,
            safety_notes=[
                "Modifies low-level kernel filesystem flags.",
                "Setting '+i' will prevent modifications even by root.",
            ],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = PermissionsBackend.apply_chattr(self.current_path, cmd_flag)
            if res.success:
                QMessageBox.information(self, "Attributes Applied", f"Updated attributes successfully!\n{cmd_str}")
                self._inspect_path()
            else:
                QMessageBox.critical(self, "Failed", f"Error:\n{res.stderr or res.stdout}")
