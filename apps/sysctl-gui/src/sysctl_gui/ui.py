"""User interface for Linux kernel parameter tuner (sysctl)."""

import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from linux_gui_core.runner.package_manager import PackageManagerInspector
from linux_gui_core.widgets.loading_modal import run_with_loading_modal
from linux_gui_core.widgets.package_badge import PackageOwnershipBadge
from linux_gui_core.widgets.preview_banner import LivePreviewBanner
from linux_gui_core.widgets.safety_dialog import SafetyExecutionDialog, generate_diff
from linux_gui_core.widgets.tooltips import format_tooltip
from sysctl_gui.backend import PRESET_BY_KEY, SYSCTL_PRESETS, SysctlBackend, SysctlPreset
from sysctl_gui.strings import tr


class SysctlMainWindow(QMainWindow):
    """Main window for inspecting and configuring live and persistent sysctl kernel parameters."""

    TARGET_CONF = "/etc/sysctl.d/99-sysctl.conf"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("window_title"))
        self.resize(1280, 760)
        self.setMinimumSize(960, 680)

        self.selected_preset: SysctlPreset | None = SYSCTL_PRESETS[0]
        self.active_key: str = SYSCTL_PRESETS[0].key
        self.active_live_value: str = ""
        self.live_values_by_key: dict[str, str] = {}
        self.all_params: list[tuple[str, str]] = []
        self._is_updating_ui: bool = False

        self._init_ui()
        self._load_config_files()
        self._load_presets()
        self._update_preview()

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
            man_pages=[
                "sysctl(8)",
                "sysctl.conf(5)",
                "sysctl.d(5)",
                "proc_sys(5)",
                "proc_sys_vm(5)",
                "proc_sys_kernel(5)",
                "proc_sys_fs(5)",
                "proc_sys_net(5)",
                "tcp(7)",
                "ip(7)",
                "icmp(7)",
                "inotify(7)",
            ],
        )
        self.preview_banner.diffRequested.connect(self._inspect_diff)
        layout.addWidget(self.preview_banner)

        # 2. Top Drop-in File Selection Bar (/etc/sysctl.d/*.conf)
        file_bar = QHBoxLayout()
        file_bar.setSpacing(8)

        lbl_conf = QLabel(tr("lbl_target_conf"))
        lbl_conf_tip = format_tooltip(
            "Persistent sysctl.d Drop-in File",
            "/etc/sysctl.d/99-sysctl.conf",
            "systemd-sysctl(8) reads drop-in files from /etc/sysctl.d/*.conf in lexicographical order at boot. "
            "Files beginning with a high number (such as 99-sysctl.conf or 99-custom.conf) are applied last and override earlier defaults.",
            default_value="/etc/sysctl.d/99-sysctl.conf",
            man_page="sysctl.d(5)",
        )
        lbl_conf.setToolTip(lbl_conf_tip)
        file_bar.addWidget(lbl_conf)

        self.cmb_files = QComboBox()
        self.cmb_files.setMinimumWidth(300)
        self.cmb_files.setToolTip(lbl_conf_tip)
        self.cmb_files.currentTextChanged.connect(self._on_file_selected)
        file_bar.addWidget(self.cmb_files)

        self.pkg_badge = PackageOwnershipBadge()
        file_bar.addWidget(self.pkg_badge)

        btn_new_file = QPushButton(tr("btn_new_file"))
        btn_new_file.setToolTip(format_tooltip(
            "Create New sysctl.d Drop-in File",
            "/etc/sysctl.d/90-network.conf",
            "Creates or selects a separate modular configuration file in /etc/sysctl.d/ so you can group related kernel parameters (e.g. 90-network.conf or 99-vm.conf).",
            man_page="sysctl.d(5)",
        ))
        btn_new_file.clicked.connect(self._prompt_new_file)
        file_bar.addWidget(btn_new_file)

        file_bar.addStretch()

        btn_reload_system = QPushButton(tr("btn_reload_system"))
        btn_reload_system.setToolTip(format_tooltip(
            "Reload All System Kernel Configs",
            "sudo sysctl --system",
            "Reloads all persistent configuration files from /etc/sysctl.d/, /run/sysctl.d/, and /usr/lib/sysctl.d/ immediately without rebooting.",
            man_page="sysctl(8)",
        ))
        btn_reload_system.clicked.connect(self._reload_system_configs)
        file_bar.addWidget(btn_reload_system)

        layout.addLayout(file_bar)

        # 3. Main Vertical Splitter: Tabs on Top, Shared Parameter Inspector & Editor on Bottom
        main_splitter = QSplitter(Qt.Orientation.Vertical)

        self.tabs = QTabWidget()

        # --- Tab 1: Documented Kernel Parameters ---
        tab_presets = QWidget()
        preset_layout = QVBoxLayout(tab_presets)
        preset_layout.setContentsMargins(6, 6, 6, 6)
        preset_layout.setSpacing(8)

        preset_filter_bar = QHBoxLayout()
        preset_filter_bar.setSpacing(8)

        lbl_cat = QLabel(tr("lbl_category_filter"))
        cat_tip = format_tooltip(
            "Filter by Kernel Subsystem Category",
            "Memory & Writeback / Networking & TCP/IP / File System & Limits / Kernel & Security",
            "Filters the documented kernel parameters table by subsystem area corresponding to /proc/sys/ subdirectories (vm, net, fs, kernel).",
            default_value="All Categories",
            man_page="proc_sys(5)",
        )
        lbl_cat.setToolTip(cat_tip)
        preset_filter_bar.addWidget(lbl_cat)

        self.cmb_category = QComboBox()
        self.cmb_category.setToolTip(cat_tip)
        categories = [tr("opt_all_categories")] + list(dict.fromkeys(p.category for p in SYSCTL_PRESETS))
        self.cmb_category.addItems(categories)
        self.cmb_category.currentTextChanged.connect(self._filter_presets_table)
        preset_filter_bar.addWidget(self.cmb_category)

        lbl_psearch = QLabel(tr("lbl_preset_search"))
        psearch_tip = format_tooltip(
            "Filter Documented Kernel Parameters",
            "swappiness, tcp, inotify, ptrace",
            "Filters the documented parameters table by key name, title, description, or man page reference.",
            can_be_blank=True,
            blank_behavior="Shows all parameters in the selected category",
            man_page="proc_sys(5)",
        )
        lbl_psearch.setToolTip(psearch_tip)
        preset_filter_bar.addWidget(lbl_psearch)

        self.txt_search_presets = QLineEdit()
        self.txt_search_presets.setPlaceholderText(tr("placeholder_preset_search"))
        self.txt_search_presets.setToolTip(psearch_tip)
        self.txt_search_presets.textChanged.connect(self._filter_presets_table)
        preset_filter_bar.addWidget(self.txt_search_presets, 1)

        btn_refresh = QPushButton(tr("btn_refresh_live"))
        btn_refresh.setToolTip(format_tooltip(
            "Re-read Live Kernel Values",
            "cat /proc/sys/...",
            "Re-queries the active Linux kernel values from /proc/sys/ for all documented parameters.",
            man_page="proc_sys(5)",
        ))
        btn_refresh.clicked.connect(self._load_presets)
        preset_filter_bar.addWidget(btn_refresh)

        preset_layout.addLayout(preset_filter_bar)

        self.tbl_presets = QTableWidget(0, 5)
        self.tbl_presets.setHorizontalHeaderLabels([
            tr("col_category"),
            tr("col_param_key"),
            tr("col_live_val"),
            tr("col_kernel_default"),
            tr("col_valid_range"),
        ])
        self.tbl_presets.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_presets.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tbl_presets.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.tbl_presets.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.tbl_presets.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.tbl_presets.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.tbl_presets.setColumnWidth(0, 175)
        self.tbl_presets.setColumnWidth(1, 250)
        self.tbl_presets.setColumnWidth(2, 140)
        self.tbl_presets.setColumnWidth(3, 130)
        self.tbl_presets.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_presets.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl_presets.itemSelectionChanged.connect(self._on_preset_selected)
        preset_layout.addWidget(self.tbl_presets)

        self.tabs.addTab(tab_presets, tr("tab_presets"))

        # --- Tab 2: Full Parameter Explorer (sysctl -a) ---
        tab_all = QWidget()
        all_layout = QVBoxLayout(tab_all)
        all_layout.setContentsMargins(6, 6, 6, 6)
        all_layout.setSpacing(8)

        search_bar = QHBoxLayout()
        search_bar.setSpacing(8)
        lbl_all_search = QLabel(tr("lbl_search_param"))
        all_search_tip = format_tooltip(
            "Search All Kernel Parameters (sysctl -a)",
            "net.ipv4.tcp, vm., fs.inotify",
            "Filters the complete table of runtime kernel parameters exposed under /proc/sys/. Select any row to inspect or modify it in the editor pane below.",
            can_be_blank=True,
            blank_behavior="Shows all queried kernel parameters",
            man_page="sysctl(8)",
        )
        lbl_all_search.setToolTip(all_search_tip)
        search_bar.addWidget(lbl_all_search)

        self.txt_search_all = QLineEdit()
        self.txt_search_all.setPlaceholderText(tr("placeholder_search_param"))
        self.txt_search_all.setToolTip(all_search_tip)
        self.txt_search_all.textChanged.connect(self._filter_all_params)
        search_bar.addWidget(self.txt_search_all, 1)

        btn_load_all = QPushButton(tr("btn_query_all"))
        btn_load_all.setToolTip(format_tooltip(
            "Query All Runtime Kernel Parameters",
            "sysctl -a",
            "Executes 'sysctl -a' to read all available runtime kernel variables from /proc/sys/. Select any parameter in the table to load it into the editor below.",
            man_page="sysctl(8)",
        ))
        btn_load_all.clicked.connect(self._load_all_parameters)
        search_bar.addWidget(btn_load_all)
        all_layout.addLayout(search_bar)

        self.tbl_all = QTableWidget(0, 3)
        self.tbl_all.setHorizontalHeaderLabels([
            tr("col_all_name"),
            tr("col_all_val"),
            tr("col_all_man"),
        ])
        self.tbl_all.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_all.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tbl_all.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_all.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_all.setColumnWidth(0, 380)
        self.tbl_all.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_all.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl_all.itemSelectionChanged.connect(self._on_all_table_selected)
        all_layout.addWidget(self.tbl_all)

        self.tabs.addTab(tab_all, tr("tab_all"))
        main_splitter.addWidget(self.tabs)

        # --- Bottom Pane: Shared Selected Parameter Inspector & Value Editor ---
        info_box = QGroupBox(tr("group_param_info"))
        info_grid = QGridLayout(info_box)
        info_grid.setContentsMargins(12, 10, 12, 10)
        info_grid.setSpacing(8)

        self.lbl_param_title = QLabel("")
        self.lbl_param_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #6899e6;")
        info_grid.addWidget(self.lbl_param_title, 0, 0, 1, 2)

        self.lbl_param_key = QLabel("")
        info_grid.addWidget(self.lbl_param_key, 1, 0)

        self.lbl_param_range = QLabel("")
        self.lbl_param_range.setStyleSheet("color: #9498a1;")
        info_grid.addWidget(self.lbl_param_range, 1, 1)

        self.lbl_param_desc = QLabel("")
        self.lbl_param_desc.setWordWrap(True)
        self.lbl_param_desc.setStyleSheet("color: #e3e5e8; line-height: 1.4; padding: 2px 0;")
        info_grid.addWidget(self.lbl_param_desc, 2, 0, 1, 2)

        # Documented value presets & target value input bar
        input_bar = QHBoxLayout()
        input_bar.setSpacing(8)

        lbl_doc_vals = QLabel(tr("lbl_documented_values"))
        doc_vals_tip = format_tooltip(
            "Documented Kernel Parameter Values",
            "60 — Upstream kernel default",
            "Lists standard values and bitmasks documented in the Linux kernel man pages (proc_sys(5), tcp(7), ip(7), etc.). Selecting an entry populates the Target Value field.",
            man_page="proc_sys(5)",
        )
        lbl_doc_vals.setToolTip(doc_vals_tip)
        input_bar.addWidget(lbl_doc_vals)

        self.cmb_value_options = QComboBox()
        self.cmb_value_options.setMinimumWidth(340)
        self.cmb_value_options.setToolTip(doc_vals_tip)
        self.cmb_value_options.currentIndexChanged.connect(self._on_documented_value_chosen)
        input_bar.addWidget(self.cmb_value_options)

        lbl_target = QLabel(tr("lbl_target_value"))
        target_tip = format_tooltip(
            "Target Parameter Value",
            "key = value",
            "The value to write to /proc/sys/ (via sysctl -w) or save persistently in /etc/sysctl.d/*.conf.",
            can_be_blank=False,
            man_page="sysctl.conf(5)",
        )
        lbl_target.setToolTip(target_tip)
        input_bar.addWidget(lbl_target)

        self.txt_new_val = QLineEdit()
        self.txt_new_val.setMaximumWidth(160)
        self.txt_new_val.setToolTip(target_tip)
        self.txt_new_val.textChanged.connect(self._update_preview)
        input_bar.addWidget(self.txt_new_val)

        self.btn_use_default = QPushButton(tr("btn_use_default"))
        self.btn_use_default.setToolTip(format_tooltip(
            "Reset to Upstream Kernel Default",
            "vm.swappiness = 60",
            "Populates the Target Value input with the standard upstream Linux kernel default value documented in the man page.",
            man_page="proc_sys(5)",
        ))
        self.btn_use_default.clicked.connect(self._fill_kernel_default)
        input_bar.addWidget(self.btn_use_default)

        self.btn_use_live = QPushButton(tr("btn_use_live"))
        self.btn_use_live.setToolTip(format_tooltip(
            "Copy Current Live Kernel Value",
            "cat /proc/sys/...",
            "Populates the Target Value input with the value currently active in running kernel memory.",
            man_page="proc_sys(5)",
        ))
        self.btn_use_live.clicked.connect(self._fill_live_value)
        input_bar.addWidget(self.btn_use_live)

        input_bar.addStretch()

        btn_live = QPushButton(tr("btn_apply_live"))
        btn_live.setToolTip(format_tooltip(
            tr("tooltip_apply_live_title"),
            tr("tooltip_apply_live_cmd"),
            tr("tooltip_apply_live_desc"),
            tr("tooltip_apply_live_safety"),
            man_page="sysctl(8)",
        ))
        btn_live.clicked.connect(self._apply_live)
        input_bar.addWidget(btn_live)

        btn_persist = QPushButton(tr("btn_save_persistent"))
        btn_persist.setObjectName("primaryBtn")
        btn_persist.setToolTip(format_tooltip(
            tr("tooltip_save_persist_title"),
            tr("tooltip_save_persist_cmd"),
            tr("tooltip_save_persist_desc"),
            tr("tooltip_save_persist_safety"),
            man_page="sysctl.d(5)",
        ))
        btn_persist.clicked.connect(self._apply_persistent)
        input_bar.addWidget(btn_persist)

        info_grid.addLayout(input_bar, 3, 0, 1, 2)
        main_splitter.addWidget(info_box)
        main_splitter.setStretchFactor(0, 3)
        main_splitter.setStretchFactor(1, 1)

        layout.addWidget(main_splitter, 1)

    def _current_target_conf(self) -> str:
        text = self.cmb_files.currentText().strip()
        return text if text else self.TARGET_CONF

    def _load_config_files(self) -> None:
        files = SysctlBackend.list_config_files()
        current = self.cmb_files.currentText()
        self.cmb_files.blockSignals(True)
        self.cmb_files.clear()
        self.cmb_files.addItems(files)
        if current in files:
            self.cmb_files.setCurrentText(current)
        elif self.TARGET_CONF in files:
            self.cmb_files.setCurrentText(self.TARGET_CONF)
        self.cmb_files.blockSignals(False)
        self._on_file_selected(self.cmb_files.currentText())

    def _on_file_selected(self, path: str) -> None:
        if path:
            self.TARGET_CONF = path
            ownership = run_with_loading_modal(
                self,
                title="Checking Configuration File...",
                subtitle=f"Inspecting package ownership for {os.path.basename(path)}...",
                task_fn=lambda: PackageManagerInspector.check_file_owner(path),
            )
            self.pkg_badge.update_status(ownership, path)
            self._update_preview()

    def _prompt_new_file(self) -> None:
        name, ok = QInputDialog.getText(
            self,
            tr("dialog_new_file_title"),
            tr("dialog_new_file_prompt"),
            text="99-custom.conf",
        )
        if ok and name.strip():
            clean = name.strip()
            if not clean.endswith(".conf"):
                clean += ".conf"
            full_path = os.path.join("/etc/sysctl.d", os.path.basename(clean))
            if self.cmb_files.findText(full_path) == -1:
                self.cmb_files.addItem(full_path)
            self.cmb_files.setCurrentText(full_path)

    def _load_presets(self) -> None:
        live_values = run_with_loading_modal(
            self,
            title="Loading Kernel Parameters...",
            subtitle="Reading live /proc/sys values...",
            task_fn=lambda: [SysctlBackend.get_live_value(p.key) for p in SYSCTL_PRESETS],
        )
        self.live_values_by_key = {
            p.key: live_val for p, live_val in zip(SYSCTL_PRESETS, live_values)
        }
        self._is_updating_ui = True
        self.tbl_presets.setRowCount(0)
        for row, (p, live_val) in enumerate(zip(SYSCTL_PRESETS, live_values)):
            self.tbl_presets.insertRow(row)
            range_ref = f"{p.typical_range} · {p.man_page}"
            cells = [
                QTableWidgetItem(p.category),
                QTableWidgetItem(p.key),
                QTableWidgetItem(live_val),
                QTableWidgetItem(p.kernel_default),
                QTableWidgetItem(range_ref),
            ]
            row_tip = format_tooltip(
                f"{p.title} ({p.key})",
                f"{p.key} = {p.kernel_default}",
                p.description,
                security=p.security_note or None,
                default_value=f"{p.kernel_default} ({p.typical_range})",
                man_page=p.man_page,
            )
            for col, item in enumerate(cells):
                item.setToolTip(row_tip)
                self.tbl_presets.setItem(row, col, item)
            self.tbl_presets.item(row, 0).setData(Qt.ItemDataRole.UserRole, p)

        self._is_updating_ui = False
        self._filter_presets_table()
        if self.tbl_presets.rowCount() > 0 and not self.tbl_presets.selectedItems():
            self.tbl_presets.selectRow(0)
        elif self.selected_preset is not None:
            self._populate_inspector_from_preset(self.selected_preset)

    def _filter_presets_table(self, *_args) -> None:
        selected_cat = self.cmb_category.currentText()
        all_cats_label = tr("opt_all_categories")
        needle = self.txt_search_presets.text().strip().lower()

        for row in range(self.tbl_presets.rowCount()):
            item0 = self.tbl_presets.item(row, 0)
            if not item0:
                continue
            preset: SysctlPreset = item0.data(Qt.ItemDataRole.UserRole)
            cat_match = (selected_cat == all_cats_label) or (preset.category == selected_cat)
            text_match = (
                not needle
                or needle in preset.key.lower()
                or needle in preset.title.lower()
                or needle in preset.description.lower()
                or needle in preset.man_page.lower()
            )
            self.tbl_presets.setRowHidden(row, not (cat_match and text_match))

    def _on_preset_selected(self) -> None:
        if self._is_updating_ui:
            return
        selected = self.tbl_presets.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        preset: SysctlPreset = self.tbl_presets.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self._populate_inspector_from_preset(preset)

    def _populate_inspector_from_preset(self, preset: SysctlPreset) -> None:
        self.selected_preset = preset
        self.active_key = preset.key
        live_val = self.live_values_by_key.get(preset.key) or SysctlBackend.get_live_value(preset.key)
        self.active_live_value = live_val

        self.lbl_param_title.setText(preset.title)
        self.lbl_param_key.setText(
            tr(
                "lbl_param_key_format",
                key=preset.key,
                category=preset.category,
                man_page=preset.man_page,
            )
        )
        self.lbl_param_range.setText(
            tr(
                "lbl_param_range_format",
                live=live_val,
                default=preset.kernel_default,
                range=preset.typical_range,
            )
        )
        desc_text = preset.description
        if preset.security_note:
            desc_text = f"{preset.description}\nSecurity Note: {preset.security_note}"
        self.lbl_param_desc.setText(desc_text)

        self.cmb_value_options.blockSignals(True)
        self.cmb_value_options.clear()
        self.cmb_value_options.addItem(tr("opt_select_documented"), "")
        for val_str, label_str in preset.value_options:
            self.cmb_value_options.addItem(label_str, val_str)
        self.cmb_value_options.setEnabled(bool(preset.value_options))
        self.cmb_value_options.blockSignals(False)

        self.btn_use_default.setEnabled(True)
        initial_val = live_val if live_val and live_val != "(unavailable)" else preset.kernel_default
        self.txt_new_val.setText(initial_val)
        self._update_preview()

    def _populate_inspector_from_raw_key(self, key: str, live_val: str) -> None:
        preset = PRESET_BY_KEY.get(key)
        if preset is not None:
            self.live_values_by_key[key] = live_val
            self._populate_inspector_from_preset(preset)
            return

        self.selected_preset = None
        self.active_key = key
        self.active_live_value = live_val
        man_page = SysctlBackend.infer_man_page_for_key(key)
        subsystem = key.split(".", 1)[0] if "." in key else "kernel"

        self.lbl_param_title.setText(key)
        self.lbl_param_key.setText(
            tr(
                "lbl_param_key_format",
                key=key,
                category=f"/proc/sys/{subsystem}/",
                man_page=man_page,
            )
        )
        self.lbl_param_range.setText(
            tr(
                "lbl_param_range_format",
                live=live_val,
                default="(see man page)",
                range=f"Documented in {man_page}",
            )
        )
        self.lbl_param_desc.setText(tr("desc_custom_param", man_page=man_page))

        self.cmb_value_options.blockSignals(True)
        self.cmb_value_options.clear()
        self.cmb_value_options.addItem(tr("opt_select_documented"), "")
        self.cmb_value_options.setEnabled(False)
        self.cmb_value_options.blockSignals(False)

        self.btn_use_default.setEnabled(False)
        self.txt_new_val.setText(live_val)
        self._update_preview()

    def _on_documented_value_chosen(self, index: int) -> None:
        if index <= 0:
            return
        val = self.cmb_value_options.itemData(index)
        if val is not None and str(val) != "":
            self.txt_new_val.setText(str(val))

    def _fill_kernel_default(self) -> None:
        if self.selected_preset:
            self.txt_new_val.setText(self.selected_preset.kernel_default)

    def _fill_live_value(self) -> None:
        if self.active_live_value and self.active_live_value != "(unavailable)":
            self.txt_new_val.setText(self.active_live_value)

    def _fill_recommended(self) -> None:
        """Backwards-compatible alias that resets to the kernel default."""
        self._fill_kernel_default()

    def _update_preview(self) -> None:
        if not self.active_key:
            return
        val = self.txt_new_val.text().strip()
        conf = self._current_target_conf()
        cmd_str = f"sudo sysctl -w {self.active_key}={val}  |  {conf}: {self.active_key} = {val}"
        self.preview_banner.set_text(cmd_str)

    def _inspect_diff(self) -> None:
        if not self.active_key:
            return
        val = self.txt_new_val.text().strip()
        conf = self._current_target_conf()
        existing = SysctlBackend.read_config_file(conf)
        updated = SysctlBackend.build_updated_config_content(self.active_key, val, existing)
        diff_txt = generate_diff(existing, updated, filepath=conf)
        dlg = SafetyExecutionDialog(
            title=tr("dialog_diff_title"),
            target_path_or_command=conf,
            diff_text=diff_txt,
            safety_notes=[tr("note_diff_preview", conf=conf)],
            parent=self,
        )
        dlg.exec()

    def _reload_system_configs(self) -> None:
        dlg = SafetyExecutionDialog(
            title=tr("dialog_reload_title"),
            target_path_or_command="sudo sysctl --system",
            safety_notes=[tr("note_reload_desc")],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = SysctlBackend.reload_all_configs()
            if res.success:
                QMessageBox.information(self, tr("title_reloaded"), tr("msg_reloaded"))
                self._load_presets()
            else:
                QMessageBox.critical(self, tr("title_failed"), tr("msg_live_failed", error=res.stderr or res.stdout))

    def _apply_live(self) -> None:
        if not self.active_key:
            return
        key = self.active_key
        val = self.txt_new_val.text().strip()
        if not val:
            QMessageBox.warning(self, tr("title_empty_value"), tr("msg_empty_value"))
            return
        cmd = f"sudo sysctl -w {key}={val}"

        dlg = SafetyExecutionDialog(
            title=tr("dialog_live_title"),
            target_path_or_command=cmd,
            safety_notes=[
                tr("note_live_memory"),
                tr("note_live_temporary"),
                tr("note_live_safe"),
            ],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = SysctlBackend.apply_live_value(key, val)
            if res.success:
                QMessageBox.information(self, tr("title_live_applied"), tr("msg_live_applied", cmd=cmd))
                self._load_presets()
            else:
                QMessageBox.critical(self, tr("title_failed"), tr("msg_live_failed", error=res.stderr or res.stdout))

    def _apply_persistent(self) -> None:
        if not self.active_key:
            return
        key = self.active_key
        val = self.txt_new_val.text().strip()
        if not val:
            QMessageBox.warning(self, tr("title_empty_value"), tr("msg_empty_value"))
            return
        conf = self._current_target_conf()
        existing = SysctlBackend.read_config_file(conf)
        updated = SysctlBackend.build_updated_config_content(key, val, existing)
        diff_txt = generate_diff(existing, updated, filepath=conf)

        dlg = SafetyExecutionDialog(
            title=tr("dialog_persist_title"),
            target_path_or_command=f"{conf}  &&  sudo sysctl --system",
            diff_text=diff_txt,
            safety_notes=[
                tr("note_persist_write", key=key, val=val, conf=conf),
                tr("note_persist_reload"),
                tr("note_persist_reboot"),
            ],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = SysctlBackend.save_persistent_config(key, val, conf)
            if res.success:
                QMessageBox.information(self, tr("title_saved_permanent"), tr("msg_saved_permanent", conf=conf))
                self._load_config_files()
                self._load_presets()
            else:
                QMessageBox.critical(self, tr("title_failed"), tr("msg_persist_failed", error=res.stderr or res.stdout))

    def _load_all_parameters(self) -> None:
        self.all_params = run_with_loading_modal(
            self,
            title="Loading All Kernel Parameters...",
            subtitle="Querying sysctl -a parameter table...",
            task_fn=SysctlBackend.list_all_parameters,
        )
        self.tbl_all.setRowCount(0)
        for row, (k, v) in enumerate(self.all_params):
            self.tbl_all.insertRow(row)
            man_ref = SysctlBackend.infer_man_page_for_key(k)
            preset = PRESET_BY_KEY.get(k)
            tip = format_tooltip(
                preset.title if preset else k,
                f"{k} = {v}",
                preset.description if preset else tr("desc_custom_param", man_page=man_ref),
                default_value=preset.kernel_default if preset else None,
                security=preset.security_note if (preset and preset.security_note) else None,
                man_page=man_ref,
            )
            items = [
                QTableWidgetItem(k),
                QTableWidgetItem(v),
                QTableWidgetItem(man_ref),
            ]
            for col, item in enumerate(items):
                item.setToolTip(tip)
                self.tbl_all.setItem(row, col, item)
        self._filter_all_params(self.txt_search_all.text())

    def _filter_all_params(self, text: str) -> None:
        needle = text.lower().strip()
        for row in range(self.tbl_all.rowCount()):
            k_item = self.tbl_all.item(row, 0)
            v_item = self.tbl_all.item(row, 1)
            matches = bool(
                (k_item and needle in k_item.text().lower())
                or (v_item and needle in v_item.text().lower())
            )
            self.tbl_all.setRowHidden(row, not matches)

    def _on_all_table_selected(self) -> None:
        selected = self.tbl_all.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        k = self.tbl_all.item(row, 0).text()
        v = self.tbl_all.item(row, 1).text()
        self._populate_inspector_from_raw_key(k, v)
