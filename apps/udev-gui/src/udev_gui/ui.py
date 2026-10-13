"""User interface for udev rules manager."""

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
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from linux_gui_core.runner.executor import SafeExecutor
from linux_gui_core.runner.package_manager import PackageManagerInspector, PackageOwnership
from linux_gui_core.widgets.package_badge import PackageOwnershipBadge
from linux_gui_core.widgets.preview_banner import LivePreviewBanner
from linux_gui_core.widgets.safety_dialog import SafetyExecutionDialog, generate_diff
from linux_gui_core.widgets.tooltips import format_tooltip
from udev_gui.parser import UdevParser, UdevRule
from udev_gui.strings import tr


ADVANCED_UDEV_PRESETS = [
    (
        'ATTR{power/wakeup}="disabled"',
        "Disable Sleep / Wakeup",
        "Prevents this device from waking the PC from suspend/sleep. Commonly used to stop accidental keyboard or mouse wakeups.",
        "Safe / Recommended for problematic keyboards/mice",
    ),
    (
        'ATTR{power/wakeup}="enabled"',
        "Enable Sleep / Wakeup",
        "Explicitly allows this USB device to wake the computer from sleep when a key or button is pressed.",
        "Safe",
    ),
    (
        'ATTR{power/control}="auto"',
        "Enable USB Autosuspend",
        "Enables kernel runtime power-saving autosuspend when device is idle.",
        "Safe / Power Saving",
    ),
    (
        'ATTR{power/control}="on"',
        "Disable USB Autosuspend",
        "Prevents kernel from putting USB device to sleep; keeps port continuously powered.",
        "Safe / Stability fix for audio/serial interfaces",
    ),
    (
        'OPTIONS+="static_node=uinput"',
        "Static Device Node",
        "Ensures static device node exists in /dev prior to daemon startup.",
        "Safe / Virtual input devices",
    ),
    (
        'TAG+="udev-acl"',
        "Desktop ACL Tag",
        "Grants desktop user access via POSIX ACLs (legacy companion to uaccess).",
        "Safe",
    ),
    (
        'ENV{ID_INPUT_KEYBOARD}=="1"',
        "Match Input Keyboard",
        "Matches any device flagged by the kernel as a keyboard.",
        "Safe Match",
    ),
    (
        'ENV{ID_INPUT_MOUSE}=="1"',
        "Match Input Mouse",
        "Matches any device flagged by the kernel as a mouse/trackball.",
        "Safe Match",
    ),
]


class AdvancedAttributeDialog(QDialog):
    """Searchable dialog to select or enter advanced udev attributes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg_adv_title"))
        self.resize(640, 440)
        self.selected_token: str = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel(tr("lbl_search_attrs")))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText(tr("placeholder_search_attrs"))
        self.txt_search.textChanged.connect(self._filter_list)
        search_layout.addWidget(self.txt_search)
        layout.addLayout(search_layout)

        # Presets list
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_preset_double_clicked)
        self._populate_list()
        layout.addWidget(self.list_widget)

        # Custom entry box
        custom_box = QGroupBox(tr("group_custom_token"))
        c_layout = QHBoxLayout(custom_box)
        self.txt_custom = QLineEdit()
        self.txt_custom.setPlaceholderText(tr("placeholder_custom_token"))
        c_layout.addWidget(self.txt_custom)
        layout.addWidget(custom_box)

        # Button box
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self._accept_selection)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _populate_list(self) -> None:
        self.list_widget.clear()
        for token, title, desc, badge in ADVANCED_UDEV_PRESETS:
            item = QListWidgetItem(f"{title}  ➔  {token}\n    {desc}")
            item.setData(Qt.ItemDataRole.UserRole, token)
            self.list_widget.addItem(item)

    def _filter_list(self, text: str) -> None:
        needle = text.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(needle not in item.text().lower())

    def _on_preset_double_clicked(self, item: QListWidgetItem) -> None:
        self.selected_token = item.data(Qt.ItemDataRole.UserRole)
        self.accept()

    def _accept_selection(self) -> None:
        custom = self.txt_custom.text().strip()
        if custom:
            self.selected_token = custom
            self.accept()
            return

        cur = self.list_widget.currentItem()
        if cur:
            self.selected_token = cur.data(Qt.ItemDataRole.UserRole)
            self.accept()
        else:
            QMessageBox.warning(self, tr("title_no_selection"), tr("msg_no_selection"))


class UdevMainWindow(QMainWindow):
    """Main window for editing and testing udev rules."""

    DEFAULT_RULES_DIR = "/etc/udev/rules.d"

    def __init__(self, rules_dir: str = DEFAULT_RULES_DIR):
        super().__init__()
        self.rules_dir = rules_dir
        self.setWindowTitle(tr("window_title"))
        self.resize(1280, 720)
        self.setMinimumSize(920, 620)

        self.current_file_path: str = ""
        self.rules: list[UdevRule] = []
        self.original_raw: str = ""
        self.current_ownership = PackageOwnership(is_managed=False)
        self._is_updating_ui: bool = False

        self._init_ui()
        self._load_rules_files()

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
        self.preview_banner.diffRequested.connect(self._inspect_diff)
        layout.addWidget(self.preview_banner)

        # 2. File Selection Bar with Package Ownership Inspector
        file_bar = QHBoxLayout()
        file_bar.setSpacing(8)
        file_bar.addWidget(QLabel(tr("lbl_rule_file")))
        self.cmb_files = QComboBox()
        self.cmb_files.setMinimumWidth(300)
        self.cmb_files.currentIndexChanged.connect(self._on_file_selected)
        file_bar.addWidget(self.cmb_files)

        # Package Ownership Warning Badge
        self.package_badge = PackageOwnershipBadge()
        file_bar.addWidget(self.package_badge)

        btn_new_file = QPushButton(tr("btn_new_file"))
        btn_new_file.clicked.connect(self._create_new_rule_file)
        file_bar.addWidget(btn_new_file)

        file_bar.addStretch()

        btn_reload_daemon = QPushButton(tr("btn_reload_daemon"))
        btn_reload_daemon.setToolTip(format_tooltip(
            tr("tooltip_reload_daemon_title"),
            tr("tooltip_reload_daemon_cmd"),
            tr("tooltip_reload_daemon_desc"),
            tr("tooltip_reload_daemon_impact"),
        ))
        btn_reload_daemon.clicked.connect(self._trigger_udevadm_reload)
        file_bar.addWidget(btn_reload_daemon)

        layout.addLayout(file_bar)

        # 3. Main Splitter: Rules Table vs Interactive Builder
        splitter = QSplitter(Qt.Orientation.Vertical)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            tr("col_action"),
            tr("col_subsystem"),
            tr("col_match"),
            tr("col_permissions"),
            tr("col_advanced"),
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        splitter.addWidget(self.table)

        # Form container with scroll area for responsive no-clipping layout
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(4, 4, 4, 4)
        form_layout.setSpacing(8)

        # Match Conditions Group
        match_group = QGroupBox(tr("group_match_conditions"))
        match_grid = QGridLayout(match_group)
        match_grid.setSpacing(6)

        match_grid.addWidget(QLabel(tr("lbl_subsystem")), 0, 0)
        self.cmb_subsystem = QComboBox()
        self.cmb_subsystem.setEditable(True)
        self.cmb_subsystem.addItems(["", "usb", "tty", "input", "net", "block", "sound", "drm", "hid", "hidraw", "misc"])
        self.cmb_subsystem.setToolTip(format_tooltip(
            tr("tooltip_subsystem_title"),
            tr("tooltip_subsystem_syntax"),
            tr("tooltip_subsystem_desc"),
        ))
        self.cmb_subsystem.currentTextChanged.connect(self._on_rule_modified)
        match_grid.addWidget(self.cmb_subsystem, 0, 1)

        match_grid.addWidget(QLabel(tr("lbl_action")), 0, 2)
        self.cmb_action = QComboBox()
        self.cmb_action.addItems(["", "add", "remove", "change", "bind", "unbind"])
        self.cmb_action.setToolTip(format_tooltip(
            tr("tooltip_action_title"),
            tr("tooltip_action_syntax"),
            tr("tooltip_action_desc"),
        ))
        self.cmb_action.currentTextChanged.connect(self._on_rule_modified)
        match_grid.addWidget(self.cmb_action, 0, 3)

        match_grid.addWidget(QLabel(tr("lbl_vendor")), 1, 0)
        self.txt_vendor = QLineEdit()
        self.txt_vendor.setPlaceholderText(tr("placeholder_vendor"))
        self.txt_vendor.setToolTip(format_tooltip(
            tr("tooltip_vendor_title"),
            tr("tooltip_vendor_syntax"),
            tr("tooltip_vendor_desc"),
        ))
        self.txt_vendor.textChanged.connect(self._on_rule_modified)
        match_grid.addWidget(self.txt_vendor, 1, 1)

        match_grid.addWidget(QLabel(tr("lbl_product")), 1, 2)
        self.txt_product = QLineEdit()
        self.txt_product.setPlaceholderText(tr("placeholder_product"))
        self.txt_product.setToolTip(format_tooltip(
            tr("tooltip_product_title"),
            tr("tooltip_product_syntax"),
            tr("tooltip_product_desc"),
        ))
        self.txt_product.textChanged.connect(self._on_rule_modified)
        match_grid.addWidget(self.txt_product, 1, 3)

        match_grid.addWidget(QLabel(tr("lbl_kernel")), 2, 0)
        self.txt_kernel = QLineEdit()
        self.txt_kernel.setPlaceholderText(tr("placeholder_kernel"))
        self.txt_kernel.setToolTip(format_tooltip(
            tr("tooltip_kernel_title"),
            tr("tooltip_kernel_syntax"),
            tr("tooltip_kernel_desc"),
        ))
        self.txt_kernel.textChanged.connect(self._on_rule_modified)
        match_grid.addWidget(self.txt_kernel, 2, 1)

        form_layout.addWidget(match_group)

        # Assignment Actions Group
        assign_group = QGroupBox(tr("group_permissions"))
        assign_grid = QGridLayout(assign_group)
        assign_grid.setSpacing(6)

        assign_grid.addWidget(QLabel(tr("lbl_mode")), 0, 0)
        self.cmb_mode = QComboBox()
        self.cmb_mode.setEditable(True)
        self.cmb_mode.addItems(["", "0666", "0660", "0600"])
        self.cmb_mode.setToolTip(format_tooltip(
            tr("tooltip_mode_title"),
            tr("tooltip_mode_syntax"),
            tr("tooltip_mode_desc"),
            tr("tooltip_mode_impact"),
        ))
        self.cmb_mode.currentTextChanged.connect(self._on_rule_modified)
        assign_grid.addWidget(self.cmb_mode, 0, 1)

        assign_grid.addWidget(QLabel(tr("lbl_group")), 0, 2)
        self.cmb_group = QComboBox()
        self.cmb_group.setEditable(True)
        self.cmb_group.addItems(["", "plugdev", "dialout", "input", "audio", "video"])
        self.cmb_group.setToolTip(format_tooltip(
            tr("tooltip_group_title"),
            tr("tooltip_group_syntax"),
            tr("tooltip_group_desc"),
            tr("tooltip_group_impact"),
        ))
        self.cmb_group.currentTextChanged.connect(self._on_rule_modified)
        assign_grid.addWidget(self.cmb_group, 0, 3)

        self.chk_uaccess = QCheckBox(tr("chk_uaccess"))
        self.chk_uaccess.setToolTip(format_tooltip(
            tr("tooltip_uaccess_title"),
            tr("tooltip_uaccess_syntax"),
            tr("tooltip_uaccess_desc"),
            tr("tooltip_uaccess_impact"),
        ))
        self.chk_uaccess.toggled.connect(self._on_rule_modified)
        assign_grid.addWidget(self.chk_uaccess, 1, 0, 1, 2)

        assign_grid.addWidget(QLabel(tr("lbl_symlink")), 1, 2)
        self.txt_symlink = QLineEdit()
        self.txt_symlink.setPlaceholderText(tr("placeholder_symlink"))
        self.txt_symlink.setToolTip(format_tooltip(
            tr("tooltip_symlink_title"),
            tr("tooltip_symlink_syntax"),
            tr("tooltip_symlink_desc"),
        ))
        self.txt_symlink.textChanged.connect(self._on_rule_modified)
        assign_grid.addWidget(self.txt_symlink, 1, 3)

        form_layout.addWidget(assign_group)

        # Advanced / Extra Attributes Group (Wakeup, Power, Custom Options)
        adv_group = QGroupBox(tr("group_advanced"))
        adv_layout = QVBoxLayout(adv_group)
        adv_layout.setSpacing(6)

        adv_bar = QHBoxLayout()
        self.lbl_extra_count = QLabel(tr("lbl_extra_count"))
        self.lbl_extra_count.setStyleSheet("color: #6899e6; font-weight: bold; font-size: 11px;")
        adv_bar.addWidget(self.lbl_extra_count)
        adv_bar.addStretch()

        btn_add_adv = QPushButton(tr("btn_add_adv"))
        btn_add_adv.setToolTip(tr("tooltip_add_adv"))
        btn_add_adv.clicked.connect(self._open_advanced_dialog)
        adv_bar.addWidget(btn_add_adv)
        adv_layout.addLayout(adv_bar)

        self.tbl_extras = QTableWidget(0, 2)
        self.tbl_extras.setHorizontalHeaderLabels([tr("col_extra_directive"), tr("col_extra_action")])
        self.tbl_extras.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_extras.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tbl_extras.setColumnWidth(1, 90)
        self.tbl_extras.setFixedHeight(110)
        adv_layout.addWidget(self.tbl_extras)

        form_layout.addWidget(adv_group)

        scroll.setWidget(form_widget)
        splitter.addWidget(scroll)
        layout.addWidget(splitter)

        # Bottom Action Bar
        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)
        btn_add_rule = QPushButton(tr("btn_add_rule"))
        btn_add_rule.clicked.connect(self._add_new_rule)
        action_bar.addWidget(btn_add_rule)

        btn_del_rule = QPushButton(tr("btn_remove_rule"))
        btn_del_rule.clicked.connect(self._remove_selected_rule)
        action_bar.addWidget(btn_del_rule)

        action_bar.addStretch()

        btn_save = QPushButton(tr("btn_save_rules"))
        btn_save.setObjectName("primaryBtn")
        btn_save.clicked.connect(self._save_rules_file)
        action_bar.addWidget(btn_save)

        layout.addLayout(action_bar)

    def _load_rules_files(self) -> None:
        self.cmb_files.clear()
        files = UdevParser.list_rules_files(self.rules_dir)
        if not files:
            default_demo = os.path.join(self.rules_dir, "99-custom-devices.rules")
            self.cmb_files.addItem(default_demo)
        else:
            for f in files:
                self.cmb_files.addItem(f)

    def _on_file_selected(self) -> None:
        path = self.cmb_files.currentText()
        if not path:
            return
        self.current_file_path = path

        # Check package manager ownership
        self.current_ownership = PackageManagerInspector.check_file_owner(path)
        self.package_badge.update_status(self.current_ownership, path)

        self.rules = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.original_raw = f.read()
                for line in self.original_raw.splitlines():
                    self.rules.append(UdevParser.parse_rule_line(line))
        else:
            self.original_raw = ""

        self._populate_table()

    def _populate_table(self) -> None:
        self._is_updating_ui = True
        self.table.setRowCount(0)
        row = 0
        for rule in self.rules:
            if rule.is_comment or not rule.to_line().strip():
                continue
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(rule.action or tr("val_all")))
            self.table.setItem(row, 1, QTableWidgetItem(rule.subsystem or tr("val_all")))
            match_str = f"Vendor={rule.vendor_id or '*'} Product={rule.product_id or '*'} Kernel={rule.kernel or '*'}"
            self.table.setItem(row, 2, QTableWidgetItem(match_str))
            perm_str = f"Mode={rule.mode or 'def'} Group={rule.group or 'root'} uaccess={rule.tag_uaccess}"
            self.table.setItem(row, 3, QTableWidgetItem(perm_str))
            extra_str = ", ".join(rule.extra_tokens) if rule.extra_tokens else tr("val_none")
            self.table.setItem(row, 4, QTableWidgetItem(extra_str))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, rule)
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
        rule: UdevRule = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        self._is_updating_ui = True
        self.cmb_subsystem.setCurrentText(rule.subsystem)
        self.cmb_action.setCurrentText(rule.action)
        self.txt_vendor.setText(rule.vendor_id)
        self.txt_product.setText(rule.product_id)
        self.txt_kernel.setText(rule.kernel)
        self.cmb_mode.setCurrentText(rule.mode)
        self.cmb_group.setCurrentText(rule.group)
        self.chk_uaccess.setChecked(rule.tag_uaccess)
        self.txt_symlink.setText(rule.symlink)
        self._populate_extras_table(rule)
        self._is_updating_ui = False

        self.preview_banner.set_text(rule.to_line())

    def _populate_extras_table(self, rule: UdevRule) -> None:
        self.tbl_extras.setRowCount(0)
        for idx, token in enumerate(rule.extra_tokens):
            self.tbl_extras.insertRow(idx)
            self.tbl_extras.setItem(idx, 0, QTableWidgetItem(token))
            btn_del = QPushButton(tr("btn_remove_extra"))
            btn_del.setStyleSheet("font-size: 11px; padding: 2px 6px;")
            btn_del.clicked.connect(lambda _, t=token: self._remove_extra_token(t))
            self.tbl_extras.setCellWidget(idx, 1, btn_del)

    def _remove_extra_token(self, token: str) -> None:
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        rule: UdevRule = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if token in rule.extra_tokens:
            rule.extra_tokens.remove(token)
            self._populate_extras_table(rule)
            self._on_rule_modified()

    def _open_advanced_dialog(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, tr("title_no_rule_selected"), tr("msg_select_rule_first"))
            return
        row = selected[0].row()
        rule: UdevRule = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        dlg = AdvancedAttributeDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_token:
            if dlg.selected_token not in rule.extra_tokens:
                rule.extra_tokens.append(dlg.selected_token)
                self._populate_extras_table(rule)
                self._on_rule_modified()

    def _on_rule_modified(self) -> None:
        if self._is_updating_ui:
            return
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        rule: UdevRule = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        rule.subsystem = self.cmb_subsystem.currentText().strip()
        rule.action = self.cmb_action.currentText().strip()
        rule.vendor_id = self.txt_vendor.text().strip()
        rule.product_id = self.txt_product.text().strip()
        rule.kernel = self.txt_kernel.text().strip()
        rule.mode = self.cmb_mode.currentText().strip()
        rule.group = self.cmb_group.currentText().strip()
        rule.tag_uaccess = self.chk_uaccess.isChecked()
        rule.symlink = self.txt_symlink.text().strip()

        # Update table row text
        self._is_updating_ui = True
        self.table.item(row, 0).setText(rule.action or tr("val_all"))
        self.table.item(row, 1).setText(rule.subsystem or tr("val_all"))
        self.table.item(row, 2).setText(f"Vendor={rule.vendor_id or '*'} Product={rule.product_id or '*'} Kernel={rule.kernel or '*'}")
        self.table.item(row, 3).setText(f"Mode={rule.mode or 'def'} Group={rule.group or 'root'} uaccess={rule.tag_uaccess}")
        extra_str = ", ".join(rule.extra_tokens) if rule.extra_tokens else tr("val_none")
        self.table.item(row, 4).setText(extra_str)
        self._is_updating_ui = False

        # Live update top banner
        self.preview_banner.set_text(rule.to_line())

    def _add_new_rule(self) -> None:
        new_rule = UdevRule(
            subsystem="usb",
            action="add",
            vendor_id="1234",
            product_id="5678",
            mode="0666",
            group="plugdev",
            tag_uaccess=True,
        )
        self.rules.append(new_rule)
        self._populate_table()
        self.table.selectRow(self.table.rowCount() - 1)

    def _remove_selected_rule(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        rule = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.rules.remove(rule)
        self._populate_table()

    def _create_new_rule_file(self) -> None:
        name = "99-custom-devices.rules"
        full = os.path.join(self.rules_dir, name)
        if self.cmb_files.findText(full) == -1:
            self.cmb_files.addItem(full)
        self.cmb_files.setCurrentText(full)
        self.package_badge.set_unmanaged("custom")

    def _inspect_diff(self) -> None:
        new_content = "\n".join(r.to_line() for r in self.rules) + "\n"
        diff = generate_diff(self.original_raw, new_content, os.path.basename(self.current_file_path))
        
        notes = []
        if self.current_ownership.is_managed:
            notes.append(
                tr(
                    "note_managed_file",
                    pkg=self.current_ownership.package_name,
                    manager=self.current_ownership.package_manager,
                )
            )
        else:
            notes.append(tr("note_unmanaged_file"))

        dlg = SafetyExecutionDialog(
            title=tr("dialog_diff_title"),
            target_path_or_command=self.current_file_path,
            diff_text=diff if diff.strip() else tr("diff_no_changes"),
            safety_notes=notes,
            parent=self,
        )
        dlg.exec()

    def _trigger_udevadm_reload(self) -> None:
        cmd = "udevadm control --reload-rules && udevadm trigger"
        dlg = SafetyExecutionDialog(
            title=tr("dialog_reload_title"),
            target_path_or_command=cmd,
            safety_notes=[
                tr("note_reload_rules"),
                tr("note_trigger_events"),
            ],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = SafeExecutor.run_command(["bash", "-c", cmd], elevated=True)
            if res.success:
                QMessageBox.information(self, tr("title_reloaded"), tr("msg_reload_success"))
            else:
                QMessageBox.critical(self, tr("title_reload_failed"), tr("msg_reload_failed", error=res.stderr))

    def _save_rules_file(self) -> None:
        new_content = "\n".join(r.to_line() for r in self.rules) + "\n"
        diff = generate_diff(self.original_raw, new_content, os.path.basename(self.current_file_path))

        notes = [
            tr("note_save_elevated"),
            tr("note_save_backup"),
        ]
        if self.current_ownership.is_managed:
            notes.insert(0, tr(
                "note_save_pkg_warning",
                pkg=self.current_ownership.package_name,
                manager=self.current_ownership.package_manager,
            ))

        dlg = SafetyExecutionDialog(
            title=tr("dialog_save_title"),
            target_path_or_command=self.current_file_path,
            diff_text=diff if diff.strip() else tr("diff_no_diff"),
            safety_notes=notes,
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = SafeExecutor.safe_write_system_file(self.current_file_path, new_content)
            if res.success:
                QMessageBox.information(self, tr("title_saved"), tr("msg_saved_success", backup=res.backup_file))
                self._on_file_selected()
            else:
                QMessageBox.critical(self, tr("title_error_saving"), tr("msg_saved_failed", error=res.stderr))
