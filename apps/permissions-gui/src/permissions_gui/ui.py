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
from permissions_gui.strings import tr


class PermissionsMainWindow(QMainWindow):
    """Main application window for managing POSIX ACLs and Linux extended attributes."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("window_title"))
        self.resize(1280, 720)
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
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # 1. Top Live Preview Banner
        self.preview_banner = LivePreviewBanner(
            title=tr("preview_title"),
            subtitle=tr("preview_subtitle"),
        )
        layout.addWidget(self.preview_banner)

        # 2. Target File/Folder Selection Bar
        path_bar = QHBoxLayout()
        path_bar.setSpacing(8)
        path_bar.addWidget(QLabel(tr("lbl_target_path")))
        self.txt_path = QLineEdit(self.current_path)
        self.txt_path.returnPressed.connect(self._on_path_entered)
        path_bar.addWidget(self.txt_path)

        btn_browse_file = QPushButton(tr("btn_select_file"))
        btn_browse_file.clicked.connect(self._browse_file)
        path_bar.addWidget(btn_browse_file)

        btn_browse_dir = QPushButton(tr("btn_select_dir"))
        btn_browse_dir.clicked.connect(self._browse_dir)
        path_bar.addWidget(btn_browse_dir)

        layout.addLayout(path_bar)

        # Basic Stats Pill
        self.lbl_stats = QLabel(tr("lbl_stats_checking"))
        self.lbl_stats.setStyleSheet(
            "background-color: #18191c; border: 1px solid #3a3d45; border-radius: 3px; padding: 4px 8px; color: #6899e6; font-family: monospace; font-size: 11px;"
        )
        layout.addWidget(self.lbl_stats)

        # 3. Main Tabs: ACLs vs Attributes
        tabs = QTabWidget()

        # Tab 1: Access Control Lists (ACLs)
        tab_acl = QWidget()
        acl_layout = QVBoxLayout(tab_acl)
        acl_layout.setContentsMargins(6, 6, 6, 6)
        acl_layout.setSpacing(8)

        acl_splitter = QSplitter(Qt.Orientation.Vertical)

        # Current ACL table
        self.tbl_acls = QTableWidget(0, 4)
        self.tbl_acls.setHorizontalHeaderLabels([
            tr("col_principal_type"),
            tr("col_target_name"),
            tr("col_permissions"),
            tr("col_default_inherited"),
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
        form_layout.setContentsMargins(2, 4, 2, 4)
        form_layout.setSpacing(6)

        grant_box = QGroupBox(tr("group_grant_acl"))
        grant_grid = QGridLayout(grant_box)
        grant_grid.setSpacing(6)

        # Principal type (user vs group)
        self.rb_user = QRadioButton(tr("rb_user"))
        self.rb_user.setChecked(True)
        self.rb_group = QRadioButton(tr("rb_group"))
        self.rb_user.toggled.connect(self._update_acl_preview)
        self.rb_group.toggled.connect(self._update_acl_preview)
        grant_grid.addWidget(self.rb_user, 0, 0)
        grant_grid.addWidget(self.rb_group, 0, 1)

        grant_grid.addWidget(QLabel(tr("lbl_principal_name")), 0, 2)
        self.txt_principal = QLineEdit("alice")
        self.txt_principal.setPlaceholderText(tr("placeholder_principal"))
        self.txt_principal.setToolTip(format_tooltip(
            tr("tooltip_principal_title"),
            tr("tooltip_principal_syntax"),
            tr("tooltip_principal_desc"),
            tr("tooltip_principal_impact"),
        ))
        self.txt_principal.textChanged.connect(self._update_acl_preview)
        grant_grid.addWidget(self.txt_principal, 0, 3)

        # Permission checkboxes
        perm_bar = QHBoxLayout()
        perm_bar.addWidget(QLabel(tr("lbl_perms")))
        self.chk_read = QCheckBox(tr("chk_read"))
        self.chk_read.setChecked(True)
        self.chk_read.toggled.connect(self._update_acl_preview)
        perm_bar.addWidget(self.chk_read)

        self.chk_write = QCheckBox(tr("chk_write"))
        self.chk_write.setChecked(True)
        self.chk_write.toggled.connect(self._update_acl_preview)
        perm_bar.addWidget(self.chk_write)

        self.chk_exec = QCheckBox(tr("chk_exec"))
        self.chk_exec.toggled.connect(self._update_acl_preview)
        perm_bar.addWidget(self.chk_exec)
        perm_bar.addStretch()
        grant_grid.addLayout(perm_bar, 1, 0, 1, 2)

        # Flags: default (-d) and recursive (-R)
        flags_bar = QHBoxLayout()
        self.chk_default = QCheckBox(tr("chk_default"))
        self.chk_default.setToolTip(format_tooltip(
            tr("tooltip_default_title"),
            tr("tooltip_default_syntax"),
            tr("tooltip_default_desc"),
            tr("tooltip_default_impact"),
        ))
        self.chk_default.toggled.connect(self._update_acl_preview)
        flags_bar.addWidget(self.chk_default)

        self.chk_recursive = QCheckBox(tr("chk_recursive"))
        self.chk_recursive.setToolTip(format_tooltip(
            tr("tooltip_recursive_title"),
            tr("tooltip_recursive_syntax"),
            tr("tooltip_recursive_desc"),
        ))
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
        acl_action_bar.setSpacing(8)
        btn_apply_acl = QPushButton(tr("btn_apply_acl"))
        btn_apply_acl.setObjectName("primaryBtn")
        btn_apply_acl.clicked.connect(self._apply_acl_entry)
        acl_action_bar.addWidget(btn_apply_acl)

        btn_rm_acl = QPushButton(tr("btn_remove_acl"))
        btn_rm_acl.setToolTip(tr("tooltip_remove_acl"))
        btn_rm_acl.clicked.connect(self._remove_selected_acl)
        acl_action_bar.addWidget(btn_rm_acl)

        acl_action_bar.addStretch()

        btn_strip_all = QPushButton(tr("btn_strip_all_acls"))
        btn_strip_all.setToolTip(tr("tooltip_strip_all_acls"))
        btn_strip_all.clicked.connect(self._strip_all_acls)
        acl_action_bar.addWidget(btn_strip_all)

        acl_layout.addLayout(acl_action_bar)
        tabs.addTab(tab_acl, tr("tab_acls"))

        # Tab 2: Linux Extended File Attributes (chattr / lsattr)
        tab_attr = QWidget()
        attr_layout = QVBoxLayout(tab_attr)
        attr_layout.setContentsMargins(10, 10, 10, 10)
        attr_layout.setSpacing(8)

        status_attr_box = QGroupBox(tr("group_lsattr"))
        status_attr_layout = QVBoxLayout(status_attr_box)
        status_attr_layout.setSpacing(6)
        self.lbl_attr_raw = QLabel(tr("lbl_lsattr_loading"))
        self.lbl_attr_raw.setStyleSheet("font-size: 14px; font-weight: bold; color: #6899e6; font-family: monospace; padding: 4px;")
        status_attr_layout.addWidget(self.lbl_attr_raw)

        lbl_attr_expl = QLabel(tr("lbl_attr_expl"))
        lbl_attr_expl.setWordWrap(True)
        lbl_attr_expl.setStyleSheet("color: #9498a1; font-size: 11px;")
        status_attr_layout.addWidget(lbl_attr_expl)
        attr_layout.addWidget(status_attr_box)

        # Attributes Checkbox Form
        flags_group = QGroupBox(tr("group_configure_attrs"))
        flags_grid = QGridLayout(flags_group)
        flags_grid.setSpacing(8)

        self.chk_attr_i = QCheckBox(tr("chk_attr_i"))
        self.chk_attr_i.setToolTip(format_tooltip(
            tr("tooltip_attr_i_title"),
            tr("tooltip_attr_i_syntax"),
            tr("tooltip_attr_i_desc"),
            tr("tooltip_attr_i_impact"),
        ))
        flags_grid.addWidget(self.chk_attr_i, 0, 0)

        self.chk_attr_a = QCheckBox(tr("chk_attr_a"))
        self.chk_attr_a.setToolTip(format_tooltip(
            tr("tooltip_attr_a_title"),
            tr("tooltip_attr_a_syntax"),
            tr("tooltip_attr_a_desc"),
            tr("tooltip_attr_a_impact"),
        ))
        flags_grid.addWidget(self.chk_attr_a, 1, 0)

        self.chk_attr_d = QCheckBox(tr("chk_attr_d"))
        self.chk_attr_d.setToolTip(format_tooltip(
            tr("tooltip_attr_d_title"),
            tr("tooltip_attr_d_syntax"),
            tr("tooltip_attr_d_desc"),
        ))
        flags_grid.addWidget(self.chk_attr_d, 2, 0)

        self.chk_attr_c = QCheckBox(tr("chk_attr_c"))
        self.chk_attr_c.setToolTip(format_tooltip(
            tr("tooltip_attr_c_title"),
            tr("tooltip_attr_c_syntax"),
            tr("tooltip_attr_c_desc"),
        ))
        flags_grid.addWidget(self.chk_attr_c, 3, 0)

        self.chk_attr_s = QCheckBox(tr("chk_attr_s"))
        self.chk_attr_s.setToolTip(format_tooltip(
            tr("tooltip_attr_s_title"),
            tr("tooltip_attr_s_syntax"),
            tr("tooltip_attr_s_desc"),
        ))
        flags_grid.addWidget(self.chk_attr_s, 4, 0)

        for chk in (self.chk_attr_i, self.chk_attr_a, self.chk_attr_d, self.chk_attr_c, self.chk_attr_s):
            chk.toggled.connect(self._update_attr_preview)

        attr_layout.addWidget(flags_group)

        attr_btn_bar = QHBoxLayout()
        attr_btn_bar.addStretch()
        btn_apply_attr = QPushButton(tr("btn_apply_attrs"))
        btn_apply_attr.setObjectName("primaryBtn")
        btn_apply_attr.clicked.connect(self._apply_attributes)
        attr_btn_bar.addWidget(btn_apply_attr)
        attr_layout.addLayout(attr_btn_bar)

        attr_layout.addStretch()
        tabs.addTab(tab_attr, tr("tab_attrs"))

        layout.addWidget(tabs)

    def _browse_file(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, tr("dialog_select_file_title"), self.current_path)
        if p:
            self.txt_path.setText(p)
            self._on_path_entered()

    def _browse_dir(self) -> None:
        p = QFileDialog.getExistingDirectory(self, tr("dialog_select_dir_title"), self.current_path)
        if p:
            self.txt_path.setText(p)
            self._on_path_entered()

    def _on_path_entered(self) -> None:
        p = self.txt_path.text().strip()
        if os.path.exists(p):
            self.current_path = p
            self._inspect_path()
        else:
            QMessageBox.warning(self, tr("title_not_found"), tr("msg_path_not_found", path=p))

    def _inspect_path(self) -> None:
        p = self.current_path
        stat = PermissionsBackend.get_basic_stat(p)
        if stat:
            t_str = tr("type_dir") if stat["is_dir"] else tr("type_file")
            self.lbl_stats.setText(
                tr(
                    "lbl_stats_format",
                    path=p,
                    type_str=t_str,
                    mode=stat["mode"],
                    owner=stat["owner"],
                    group=stat["group"],
                )
            )
            self.chk_default.setEnabled(stat["is_dir"])
            if not stat["is_dir"]:
                self.chk_default.setChecked(False)

        # Inspect ACLs
        self.acl_entries = PermissionsBackend.parse_acls(p)
        self._populate_acl_table()

        # Inspect Attributes
        attr_str = PermissionsBackend.get_file_attributes(p)
        self.lbl_attr_raw.setText(tr("lbl_lsattr_format", attr=attr_str or "----"))

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
            def_str = tr("val_default_inherited") if entry.is_default else tr("val_direct")
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
            QMessageBox.warning(self, tr("title_missing_name"), tr("msg_missing_name"))
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
            title=tr("dialog_apply_acl_title"),
            target_path_or_command=cmd_str,
            safety_notes=[
                tr("note_apply_acl", perms=perms, p_type=p_type, name=name),
                tr("note_elevated_pkexec"),
            ],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = PermissionsBackend.apply_setfacl(self.current_path, p_type, name, perms, is_def, rec)
            if res.success:
                QMessageBox.information(self, tr("title_acl_applied"), tr("msg_acl_applied", command=cmd_str))
                self._inspect_path()
            else:
                QMessageBox.critical(self, tr("title_error"), tr("msg_acl_error", error=res.stderr or res.stdout))

    def _remove_selected_acl(self) -> None:
        selected = self.tbl_acls.selectedItems()
        if not selected:
            QMessageBox.warning(self, tr("title_no_selection"), tr("msg_select_acl_first"))
            return
        row = selected[0].row()
        entry: ACLEntry = self.tbl_acls.item(row, 0).data(Qt.ItemDataRole.UserRole)

        confirm = QMessageBox.question(
            self,
            tr("title_remove_acl"),
            tr("msg_confirm_remove_acl", p_type=entry.principal_type, name=entry.principal_name),
        )
        if confirm == QMessageBox.StandardButton.Yes:
            res = PermissionsBackend.remove_acl_entry(self.current_path, entry)
            if res.success:
                self._inspect_path()
            else:
                QMessageBox.critical(self, tr("title_failed"), tr("msg_failed", error=res.stderr))

    def _strip_all_acls(self) -> None:
        confirm = QMessageBox.question(
            self,
            tr("title_strip_all_acls"),
            tr("msg_confirm_strip_all", path=self.current_path),
        )
        if confirm == QMessageBox.StandardButton.Yes:
            res = PermissionsBackend.remove_all_acls(self.current_path)
            if res.success:
                self._inspect_path()
            else:
                QMessageBox.critical(self, tr("title_failed"), tr("msg_failed", error=res.stderr))

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
            QMessageBox.information(self, tr("title_no_changes"), tr("msg_no_attr_changes"))
            return

        cmd_flag = " ".join(parts)
        cmd_str = f"sudo chattr {cmd_flag} {self.current_path}"

        dlg = SafetyExecutionDialog(
            title=tr("dialog_apply_attr_title"),
            target_path_or_command=cmd_str,
            safety_notes=[
                tr("note_mod_kernel_flags"),
                tr("note_immutable_root"),
            ],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = PermissionsBackend.apply_chattr(self.current_path, cmd_flag)
            if res.success:
                QMessageBox.information(self, tr("title_attrs_applied"), tr("msg_attrs_applied", command=cmd_str))
                self._inspect_path()
            else:
                QMessageBox.critical(self, tr("title_failed"), tr("msg_failed", error=res.stderr or res.stdout))
