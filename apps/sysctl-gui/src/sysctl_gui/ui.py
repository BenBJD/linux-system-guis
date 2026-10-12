"""User interface for Linux kernel parameter tuner (sysctl)."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from linux_gui_core.widgets.preview_banner import LivePreviewBanner
from linux_gui_core.widgets.safety_dialog import SafetyExecutionDialog
from linux_gui_core.widgets.tooltips import format_tooltip
from sysctl_gui.backend import SYSCTL_PRESETS, SysctlBackend, SysctlPreset


class SysctlMainWindow(QMainWindow):
    """Main window for tuning live kernel parameters and persistent sysctl.d settings."""

    TARGET_CONF = "/etc/sysctl.d/99-custom.conf"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kernel Parameters & Tweaks (sysctl)")
        self.resize(1180, 820)
        self.setMinimumSize(960, 680)

        self.selected_preset: SysctlPreset = SYSCTL_PRESETS[0]
        self.all_params: list[tuple[str, str]] = []
        self._is_updating_ui: bool = False

        self._init_ui()
        self._load_presets()
        self._update_preview()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Top Live Preview Banner
        self.preview_banner = LivePreviewBanner(
            title="Sysctl Command Preview",
            subtitle="Shows the shell command or sysctl.d configuration line before modification.",
        )
        layout.addWidget(self.preview_banner)

        # 2. Main Tabs: Curated Presets vs All Parameters
        tabs = QTabWidget()

        # Tab 1: Curated Tweaks
        tab_presets = QWidget()
        preset_layout = QVBoxLayout(tab_presets)
        preset_layout.setContentsMargins(8, 8, 8, 8)
        preset_layout.setSpacing(10)

        preset_splitter = QSplitter(Qt.Orientation.Vertical)

        # Presets table
        self.tbl_presets = QTableWidget(0, 5)
        self.tbl_presets.setHorizontalHeaderLabels([
            "Category",
            "Parameter Key",
            "Live Kernel Value",
            "Recommended Value",
            "Safety Rating",
        ])
        self.tbl_presets.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tbl_presets.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.tbl_presets.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.tbl_presets.setColumnWidth(0, 160)
        self.tbl_presets.setColumnWidth(1, 240)
        self.tbl_presets.setColumnWidth(2, 140)
        self.tbl_presets.setColumnWidth(3, 160)
        self.tbl_presets.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_presets.itemSelectionChanged.connect(self._on_preset_selected)
        preset_splitter.addWidget(self.tbl_presets)

        # Bottom detail pane
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        detail_container = QWidget()
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.setContentsMargins(4, 6, 4, 6)
        detail_layout.setSpacing(10)

        info_box = QGroupBox("Selected Kernel Parameter Explanation & Range")
        info_grid = QGridLayout(info_box)
        info_grid.setSpacing(8)

        self.lbl_param_title = QLabel("Swappiness Aggressiveness")
        self.lbl_param_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #89b4fa;")
        info_grid.addWidget(self.lbl_param_title, 0, 0, 1, 2)

        self.lbl_param_key = QLabel("Key: <code>vm.swappiness</code>")
        info_grid.addWidget(self.lbl_param_key, 1, 0)

        self.lbl_param_range = QLabel("Range: 0 to 200")
        self.lbl_param_range.setStyleSheet("color: #a6adc8;")
        info_grid.addWidget(self.lbl_param_range, 1, 1)

        self.lbl_param_desc = QLabel("Explanation of parameter...")
        self.lbl_param_desc.setWordWrap(True)
        self.lbl_param_desc.setStyleSheet("color: #cdd6f4; line-height: 1.4; padding: 4px 0;")
        info_grid.addWidget(self.lbl_param_desc, 2, 0, 1, 2)

        # Value input & Apply bar
        input_bar = QHBoxLayout()
        input_bar.addWidget(QLabel("New Target Value:"))
        self.txt_new_val = QLineEdit("10")
        self.txt_new_val.setMaximumWidth(160)
        self.txt_new_val.textChanged.connect(self._update_preview)
        input_bar.addWidget(self.txt_new_val)

        btn_fill_rec = QPushButton("Use Recommended")
        btn_fill_rec.clicked.connect(self._fill_recommended)
        input_bar.addWidget(btn_fill_rec)

        input_bar.addStretch()

        btn_live = QPushButton("Apply Live (sysctl -w)")
        btn_live.setToolTip(format_tooltip(
            "Live Memory Change",
            "sudo sysctl -w <key>=<val>",
            "Modifies kernel parameter in memory immediately without requiring a reboot. Note: Resets back to default on next reboot unless saved persistently.",
            "Safe Temporary Test",
        ))
        btn_live.clicked.connect(self._apply_live)
        input_bar.addWidget(btn_live)

        btn_persist = QPushButton("Save Persistent (/etc/sysctl.d/)")
        btn_persist.setObjectName("primaryBtn")
        btn_persist.setToolTip(format_tooltip(
            "Persistent Configuration",
            "write to /etc/sysctl.d/99-custom.conf && sysctl --system",
            "Writes the setting permanently so it persists across reboots, and immediately reloads the system kernel configuration.",
            "Permanent Setting",
        ))
        btn_persist.clicked.connect(self._apply_persistent)
        input_bar.addWidget(btn_persist)

        info_grid.addLayout(input_bar, 3, 0, 1, 2)
        detail_layout.addWidget(info_box)

        scroll.setWidget(detail_container)
        preset_splitter.addWidget(scroll)
        preset_layout.addWidget(preset_splitter)
        tabs.addTab(tab_presets, "Curated System Tweaks")

        # Tab 2: All Parameters
        tab_all = QWidget()
        all_layout = QVBoxLayout(tab_all)
        all_layout.setContentsMargins(8, 8, 8, 8)
        all_layout.setSpacing(10)

        search_bar = QHBoxLayout()
        search_bar.addWidget(QLabel("Search Parameter:"))
        self.txt_search_all = QLineEdit()
        self.txt_search_all.setPlaceholderText("Filter any sysctl key (e.g. tcp, inotify, core, bbr)...")
        self.txt_search_all.textChanged.connect(self._filter_all_params)
        search_bar.addWidget(self.txt_search_all)

        btn_load_all = QPushButton("Query All (sysctl -a)")
        btn_load_all.clicked.connect(self._load_all_parameters)
        search_bar.addWidget(btn_load_all)
        all_layout.addLayout(search_bar)

        self.tbl_all = QTableWidget(0, 2)
        self.tbl_all.setHorizontalHeaderLabels(["Kernel Parameter Name", "Current Live Value"])
        self.tbl_all.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tbl_all.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_all.setColumnWidth(0, 360)
        self.tbl_all.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_all.itemSelectionChanged.connect(self._on_all_table_selected)
        all_layout.addWidget(self.tbl_all)

        tabs.addTab(tab_all, "Full Parameter Explorer (sysctl -a)")

        layout.addWidget(tabs)

    def _load_presets(self) -> None:
        self._is_updating_ui = True
        self.tbl_presets.setRowCount(0)
        for row, p in enumerate(SYSCTL_PRESETS):
            live_val = SysctlBackend.get_live_value(p.key)
            self.tbl_presets.insertRow(row)
            self.tbl_presets.setItem(row, 0, QTableWidgetItem(p.category))
            self.tbl_presets.setItem(row, 1, QTableWidgetItem(p.key))
            self.tbl_presets.setItem(row, 2, QTableWidgetItem(live_val))
            self.tbl_presets.setItem(row, 3, QTableWidgetItem(p.recommended_value))
            self.tbl_presets.setItem(row, 4, QTableWidgetItem(p.safety_rating))
            self.tbl_presets.item(row, 0).setData(Qt.ItemDataRole.UserRole, p)

        self._is_updating_ui = False
        if self.tbl_presets.rowCount() > 0:
            self.tbl_presets.selectRow(0)

    def _on_preset_selected(self) -> None:
        if self._is_updating_ui:
            return
        selected = self.tbl_presets.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        preset: SysctlPreset = self.tbl_presets.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.selected_preset = preset

        self.lbl_param_title.setText(preset.title)
        self.lbl_param_key.setText(f"Key: <code>{preset.key}</code> (Category: {preset.category})")
        self.lbl_param_range.setText(f"Range & Defaults: {preset.typical_range}")
        self.lbl_param_desc.setText(preset.description)
        self.txt_new_val.setText(preset.recommended_value)

        self._update_preview()

    def _fill_recommended(self) -> None:
        if self.selected_preset:
            self.txt_new_val.setText(self.selected_preset.recommended_value)

    def _update_preview(self) -> None:
        if not self.selected_preset:
            return
        val = self.txt_new_val.text().strip()
        key = self.selected_preset.key
        cmd_str = f"sudo sysctl -w {key}={val}  &&  (persist via {self.TARGET_CONF}: {key} = {val})"
        self.preview_banner.set_text(cmd_str)

    def _apply_live(self) -> None:
        key = self.selected_preset.key
        val = self.txt_new_val.text().strip()
        cmd = f"sudo sysctl -w {key}={val}"

        dlg = SafetyExecutionDialog(
            title="Apply Live Kernel Parameter",
            target_path_or_command=cmd,
            safety_notes=[
                "Modifies active kernel memory immediately.",
                "Temporary: will reset back to default on next reboot.",
                "Safe for testing performance and responsiveness.",
            ],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = SysctlBackend.apply_live_value(key, val)
            if res.success:
                QMessageBox.information(self, "Live Setting Applied", f"Kernel parameter updated in memory!\n\n{cmd}")
                self._load_presets()
            else:
                QMessageBox.critical(self, "Failed", f"Error applying setting:\n{res.stderr or res.stdout}")

    def _apply_persistent(self) -> None:
        key = self.selected_preset.key
        val = self.txt_new_val.text().strip()
        cmd = f"echo '{key} = {val}' >> {self.TARGET_CONF} && sudo sysctl --system"

        dlg = SafetyExecutionDialog(
            title="Save Persistent Kernel Parameter",
            target_path_or_command=cmd,
            safety_notes=[
                f"Appends/updates '{key} = {val}' in {self.TARGET_CONF}",
                "Runs 'sysctl --system' to reload all system configuration files.",
                "Persists across reboots.",
            ],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = SysctlBackend.save_persistent_config(key, val, self.TARGET_CONF)
            if res.success:
                QMessageBox.information(self, "Saved Permanently", f"Setting saved to {self.TARGET_CONF} and loaded into kernel!")
                self._load_presets()
            else:
                QMessageBox.critical(self, "Failed", f"Error saving setting:\n{res.stderr or res.stdout}")

    def _load_all_parameters(self) -> None:
        self.all_params = SysctlBackend.list_all_parameters()
        self.tbl_all.setRowCount(0)
        for row, (k, v) in enumerate(self.all_params):
            self.tbl_all.insertRow(row)
            self.tbl_all.setItem(row, 0, QTableWidgetItem(k))
            self.tbl_all.setItem(row, 1, QTableWidgetItem(v))

    def _filter_all_params(self, text: str) -> None:
        needle = text.lower()
        for row in range(self.tbl_all.rowCount()):
            k_item = self.tbl_all.item(row, 0)
            matches = k_item and needle in k_item.text().lower()
            self.tbl_all.setRowHidden(row, not matches)

    def _on_all_table_selected(self) -> None:
        selected = self.tbl_all.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        k = self.tbl_all.item(row, 0).text()
        v = self.tbl_all.item(row, 1).text()
        self.preview_banner.set_text(f"sysctl -w {k}={v}")
