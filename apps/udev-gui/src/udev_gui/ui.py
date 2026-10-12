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
        self.setWindowTitle("Search & Add Advanced udev Attribute")
        self.resize(650, 450)
        self.selected_token: str = ""

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search Attributes:"))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Type 'wakeup', 'power', 'options', 'env'...")
        self.txt_search.textChanged.connect(self._filter_list)
        search_layout.addWidget(self.txt_search)
        layout.addLayout(search_layout)

        # Presets list
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_preset_double_clicked)
        self._populate_list()
        layout.addWidget(self.list_widget)

        # Custom entry box
        custom_box = QGroupBox("Or Enter Custom Token")
        c_layout = QHBoxLayout(custom_box)
        self.txt_custom = QLineEdit()
        self.txt_custom.setPlaceholderText('e.g. ATTR{power/wakeup}="disabled" or ENV{MY_VAR}=="1"')
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
            item = QListWidgetItem(f"{title}  ➜  {token}\n    {desc}")
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
            QMessageBox.warning(self, "No Selection", "Please select an attribute or type a custom token.")


class UdevMainWindow(QMainWindow):
    """Main window for editing and testing udev rules."""

    DEFAULT_RULES_DIR = "/etc/udev/rules.d"

    def __init__(self, rules_dir: str = DEFAULT_RULES_DIR):
        super().__init__()
        self.rules_dir = rules_dir
        self.setWindowTitle("udev Rule Manager & Builder")
        self.resize(1180, 820)
        self.setMinimumSize(960, 680)

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
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Top Live Preview Banner
        self.preview_banner = LivePreviewBanner(
            title="Udev Rule Preview",
            subtitle="Editing properties below changes this rule string instantaneously. Hover options to learn what they do.",
        )
        self.preview_banner.diffRequested.connect(self._inspect_diff)
        layout.addWidget(self.preview_banner)

        # 2. File Selection Bar with Package Ownership Inspector
        file_bar = QHBoxLayout()
        file_bar.addWidget(QLabel("Rule File:"))
        self.cmb_files = QComboBox()
        self.cmb_files.setMinimumWidth(320)
        self.cmb_files.currentIndexChanged.connect(self._on_file_selected)
        file_bar.addWidget(self.cmb_files)

        # Package Ownership Warning Badge
        self.package_badge = PackageOwnershipBadge()
        file_bar.addWidget(self.package_badge)

        btn_new_file = QPushButton("New File")
        btn_new_file.clicked.connect(self._create_new_rule_file)
        file_bar.addWidget(btn_new_file)

        file_bar.addStretch()

        btn_reload_daemon = QPushButton("Reload && Trigger (udevadm)")
        btn_reload_daemon.setToolTip(format_tooltip(
            "Reload Kernel Udev Rules",
            "udevadm control --reload-rules && udevadm trigger",
            "Notifies systemd-udevd to reload rules from /etc/udev/rules.d and replays device events so new permissions take effect immediately.",
            "Recommended after changes",
        ))
        btn_reload_daemon.clicked.connect(self._trigger_udevadm_reload)
        file_bar.addWidget(btn_reload_daemon)

        layout.addLayout(file_bar)

        # 3. Main Splitter: Rules Table vs Interactive Builder
        splitter = QSplitter(Qt.Orientation.Vertical)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Action", "Subsystem", "Match Attributes", "Permissions / Mode", "Advanced / Extra Attributes"])
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
        form_layout.setContentsMargins(4, 6, 4, 6)
        form_layout.setSpacing(10)

        # Match Conditions Group
        match_group = QGroupBox("Device Match Conditions (Keys using ==)")
        match_grid = QGridLayout(match_group)
        match_grid.setSpacing(8)

        match_grid.addWidget(QLabel("SUBSYSTEM=="), 0, 0)
        self.cmb_subsystem = QComboBox()
        self.cmb_subsystem.setEditable(True)
        self.cmb_subsystem.addItems(["", "usb", "tty", "input", "net", "block", "sound", "drm", "hid", "hidraw", "misc"])
        self.cmb_subsystem.setToolTip(format_tooltip(
            "Subsystem Match",
            'SUBSYSTEM=="usb"',
            "Filters events based on the kernel subsystem providing the device.<br><br><b>Can be blank</b> If blank, this rule matches devices across all kernel subsystems.",
        ))
        self.cmb_subsystem.currentTextChanged.connect(self._on_rule_modified)
        match_grid.addWidget(self.cmb_subsystem, 0, 1)

        match_grid.addWidget(QLabel("ACTION=="), 0, 2)
        self.cmb_action = QComboBox()
        self.cmb_action.addItems(["", "add", "remove", "change", "bind", "unbind"])
        self.cmb_action.setToolTip(format_tooltip(
            "Action Match",
            'ACTION=="add"',
            "Specifies the kernel event type.<br><br><b>Can be blank</b> If blank, the rule triggers for ALL events (add, remove, change). Specifying 'add' triggers only on device plug-in.",
        ))
        self.cmb_action.currentTextChanged.connect(self._on_rule_modified)
        match_grid.addWidget(self.cmb_action, 0, 3)

        match_grid.addWidget(QLabel("ATTR{idVendor}=="), 1, 0)
        self.txt_vendor = QLineEdit()
        self.txt_vendor.setPlaceholderText("e.g. 504b or 0483 (find with lsusb)")
        self.txt_vendor.setToolTip(format_tooltip(
            "Vendor ID Match",
            'ATTR{idVendor}=="xxxx"',
            "4-digit hexadecimal USB Vendor ID from 'lsusb'.<br><br><b>Can be blank</b> If blank, applies to devices from all manufacturers.",
        ))
        self.txt_vendor.textChanged.connect(self._on_rule_modified)
        match_grid.addWidget(self.txt_vendor, 1, 1)

        match_grid.addWidget(QLabel("ATTR{idProduct}=="), 1, 2)
        self.txt_product = QLineEdit()
        self.txt_product.setPlaceholderText("e.g. 320f or 5740")
        self.txt_product.setToolTip(format_tooltip(
            "Product ID Match",
            'ATTR{idProduct}=="xxxx"',
            "4-digit hexadecimal USB Product ID.<br><br><b>Can be blank</b> If blank, applies to any model from the specified vendor.",
        ))
        self.txt_product.textChanged.connect(self._on_rule_modified)
        match_grid.addWidget(self.txt_product, 1, 3)

        match_grid.addWidget(QLabel("KERNEL=="), 2, 0)
        self.txt_kernel = QLineEdit()
        self.txt_kernel.setPlaceholderText("e.g. ttyUSB*, hidraw*, sd*")
        self.txt_kernel.setToolTip(format_tooltip(
            "Kernel Name Filter",
            'KERNEL=="ttyUSB*"',
            "Matches kernel device node name with wildcards (*).<br><br><b>Can be blank</b> If blank, does not restrict by kernel node name.",
        ))
        self.txt_kernel.textChanged.connect(self._on_rule_modified)
        match_grid.addWidget(self.txt_kernel, 2, 1)

        form_layout.addWidget(match_group)

        # Assignment Actions Group
        assign_group = QGroupBox("Permissions & Identifiers (Keys using = or +=)")
        assign_grid = QGridLayout(assign_group)
        assign_grid.setSpacing(8)

        assign_grid.addWidget(QLabel('MODE="...":'), 0, 0)
        self.cmb_mode = QComboBox()
        self.cmb_mode.setEditable(True)
        self.cmb_mode.addItems(["", "0666", "0660", "0600"])
        self.cmb_mode.setToolTip(format_tooltip(
            "File Mode Permission",
            'MODE="0666"',
            "Sets file permissions for device node.<br><br><b>Can be blank</b> If blank, leaves default kernel permission (usually 0600 root-only).",
            "Caution for 0666",
        ))
        self.cmb_mode.currentTextChanged.connect(self._on_rule_modified)
        assign_grid.addWidget(self.cmb_mode, 0, 1)

        assign_grid.addWidget(QLabel('GROUP="...":'), 0, 2)
        self.cmb_group = QComboBox()
        self.cmb_group.setEditable(True)
        self.cmb_group.addItems(["", "plugdev", "dialout", "input", "audio", "video"])
        self.cmb_group.setToolTip(format_tooltip(
            "Owning Group",
            'GROUP="plugdev"',
            "Assigns device group ownership.<br><br><b>Can be blank</b> If blank, the device node remains owned by the root group.",
            "Recommended",
        ))
        self.cmb_group.currentTextChanged.connect(self._on_rule_modified)
        assign_grid.addWidget(self.cmb_group, 0, 3)

        self.chk_uaccess = QCheckBox('TAG+="uaccess" (Allow active logged-in desktop user)')
        self.chk_uaccess.setToolTip(format_tooltip(
            "systemd User Access Tag",
            'TAG+="uaccess"',
            "Modern systemd mechanism: dynamically grants read/write permissions to whoever is currently active on the desktop seat without group setup.",
            "Recommended for desktop Linux",
        ))
        self.chk_uaccess.toggled.connect(self._on_rule_modified)
        assign_grid.addWidget(self.chk_uaccess, 1, 0, 1, 2)

        assign_grid.addWidget(QLabel('SYMLINK+='), 1, 2)
        self.txt_symlink = QLineEdit()
        self.txt_symlink.setPlaceholderText("e.g. my_custom_device")
        self.txt_symlink.setToolTip(format_tooltip(
            "Persistent Symlink Alias",
            'SYMLINK+="custom_device"',
            "Creates a static alias in /dev/ pointing to this device.<br><br><b>Can be blank</b> If blank, no custom symlink is created.",
        ))
        self.txt_symlink.textChanged.connect(self._on_rule_modified)
        assign_grid.addWidget(self.txt_symlink, 1, 3)

        form_layout.addWidget(assign_group)

        # Advanced / Extra Attributes Group (Wakeup, Power, Custom Options)
        adv_group = QGroupBox("Advanced Attributes & Custom Rules (e.g. Wakeup, Power Management, Options)")
        adv_layout = QVBoxLayout(adv_group)

        adv_bar = QHBoxLayout()
        self.lbl_extra_count = QLabel("Active Extra Attributes on Selected Rule:")
        self.lbl_extra_count.setStyleSheet("color: #89b4fa; font-weight: bold;")
        adv_bar.addWidget(self.lbl_extra_count)
        adv_bar.addStretch()

        btn_add_adv = QPushButton("Search && Add Advanced Attribute (e.g. Wakeup, Power)...")
        btn_add_adv.setToolTip("Search catalog of common advanced attributes including disabling sleep wakeup from keyboards/mice, autosuspend, and custom tokens.")
        btn_add_adv.clicked.connect(self._open_advanced_dialog)
        adv_bar.addWidget(btn_add_adv)
        adv_layout.addLayout(adv_bar)

        self.tbl_extras = QTableWidget(0, 2)
        self.tbl_extras.setHorizontalHeaderLabels(["Attribute / Directive", "Action"])
        self.tbl_extras.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_extras.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tbl_extras.setColumnWidth(1, 100)
        self.tbl_extras.setFixedHeight(120)
        adv_layout.addWidget(self.tbl_extras)

        form_layout.addWidget(adv_group)

        scroll.setWidget(form_widget)
        splitter.addWidget(scroll)
        layout.addWidget(splitter)

        # Bottom Action Bar
        action_bar = QHBoxLayout()
        btn_add_rule = QPushButton("Add New Rule")
        btn_add_rule.clicked.connect(self._add_new_rule)
        action_bar.addWidget(btn_add_rule)

        btn_del_rule = QPushButton("Remove Selected")
        btn_del_rule.clicked.connect(self._remove_selected_rule)
        action_bar.addWidget(btn_del_rule)

        action_bar.addStretch()

        btn_save = QPushButton("Save && Apply Rule File")
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
            self.table.setItem(row, 0, QTableWidgetItem(rule.action or "(all)"))
            self.table.setItem(row, 1, QTableWidgetItem(rule.subsystem or "(all)"))
            match_str = f"Vendor={rule.vendor_id or '*'} Product={rule.product_id or '*'} Kernel={rule.kernel or '*'}"
            self.table.setItem(row, 2, QTableWidgetItem(match_str))
            perm_str = f"Mode={rule.mode or 'def'} Group={rule.group or 'root'} uaccess={rule.tag_uaccess}"
            self.table.setItem(row, 3, QTableWidgetItem(perm_str))
            extra_str = ", ".join(rule.extra_tokens) if rule.extra_tokens else "(none)"
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
            btn_del = QPushButton("❌ Remove")
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
            QMessageBox.warning(self, "No Rule Selected", "Please select a rule from the table first.")
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
        self.table.item(row, 0).setText(rule.action or "(all)")
        self.table.item(row, 1).setText(rule.subsystem or "(all)")
        self.table.item(row, 2).setText(f"Vendor={rule.vendor_id or '*'} Product={rule.product_id or '*'} Kernel={rule.kernel or '*'}")
        self.table.item(row, 3).setText(f"Mode={rule.mode or 'def'} Group={rule.group or 'root'} uaccess={rule.tag_uaccess}")
        extra_str = ", ".join(rule.extra_tokens) if rule.extra_tokens else "(none)"
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
                f"⚠️ CAUTION: Managed by package '{self.current_ownership.package_name}' ({self.current_ownership.package_manager}). "
                "Editing this file may cause conflict warnings or be overwritten on package upgrade."
            )
        else:
            notes.append("✓ Unmanaged configuration file. Safe for user edits.")

        dlg = SafetyExecutionDialog(
            title="Inspect Udev File Changes",
            target_path_or_command=self.current_file_path,
            diff_text=diff if diff.strip() else "# No changes",
            safety_notes=notes,
            parent=self,
        )
        dlg.exec()

    def _trigger_udevadm_reload(self) -> None:
        cmd = "udevadm control --reload-rules && udevadm trigger"
        dlg = SafetyExecutionDialog(
            title="Reload Udev Rules",
            target_path_or_command=cmd,
            safety_notes=[
                "Reloads rules into memory in systemd-udevd.",
                "Triggers kernel device event replays so permissions take effect.",
            ],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = SafeExecutor.run_command(["bash", "-c", cmd], elevated=True)
            if res.success:
                QMessageBox.information(self, "Reloaded", "udev daemon reloaded and events triggered successfully!")
            else:
                QMessageBox.critical(self, "Reload Failed", f"Failed:\n{res.stderr}")

    def _save_rules_file(self) -> None:
        new_content = "\n".join(r.to_line() for r in self.rules) + "\n"
        diff = generate_diff(self.original_raw, new_content, os.path.basename(self.current_file_path))

        notes = [
            "Writes file with elevated privileges (pkexec).",
            "Automatic timestamped backup will be created.",
        ]
        if self.current_ownership.is_managed:
            notes.insert(0, (
                f"⚠️ WARNING: This file is tracked by package '{self.current_ownership.package_name}' "
                f"({self.current_ownership.package_manager}). Modifying it directly may cause update conflicts!"
            ))

        dlg = SafetyExecutionDialog(
            title="Save Udev Rules",
            target_path_or_command=self.current_file_path,
            diff_text=diff if diff.strip() else "# No differences detected",
            safety_notes=notes,
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = SafeExecutor.safe_write_system_file(self.current_file_path, new_content)
            if res.success:
                QMessageBox.information(self, "Saved", f"Rules saved!\nBackup: {res.backup_file}")
                self._on_file_selected()
            else:
                QMessageBox.critical(self, "Error Saving", f"Failed:\n{res.stderr}")
