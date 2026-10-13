"""User interface for systemd Journal log viewer and maintenance."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from linux_gui_core.widgets.preview_banner import LivePreviewBanner
from linux_gui_core.widgets.safety_dialog import SafetyExecutionDialog
from linux_gui_core.widgets.tooltips import format_tooltip
from journal_gui.backend import JournalBackend
from journal_gui.strings import tr


PRIORITY_LEVELS = [
    ("err", "Errors & Crashes (-p err..emerg)", "Filters log levels 0 to 3 (emergency, alert, critical, error). Ideal for diagnosing service failures."),
    ("warning", "Warnings & Errors (-p warning..emerg)", "Filters log levels 0 to 4. Shows issues that may require attention alongside errors."),
    ("notice", "Normal Notices (-p notice..emerg)", "Filters log levels 0 to 5. Shows normal but significant system events."),
    ("info", "Informational (-p info..emerg)", "Filters log levels 0 to 6. Standard verbose application operational messages."),
    ("debug", "All Logs + Debug (-p debug..emerg)", "Includes detailed developer and kernel debug logs."),
    ("all", "Unfiltered (All Priorities)", "Displays raw journal stream without level filtering."),
]


class JournalMainWindow(QMainWindow):
    """Main window for exploring systemd journal logs and running vacuum cleanups."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("window_title"))
        self.resize(1280, 720)
        self.setMinimumSize(960, 680)

        self._init_ui()
        self._load_boot_sessions()
        self.execute_log_query()

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

        # 2. Scope & Quick Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)
        top_bar.addWidget(QLabel(tr("lbl_scope")))
        self.rb_system = QRadioButton(tr("rb_system"))
        self.rb_system.setChecked(True)
        self.rb_system.toggled.connect(self._on_filter_changed)
        top_bar.addWidget(self.rb_system)

        self.rb_user = QRadioButton(tr("rb_user"))
        self.rb_user.toggled.connect(self._on_filter_changed)
        top_bar.addWidget(self.rb_user)

        top_bar.addStretch()

        btn_refresh = QPushButton(tr("btn_refresh"))
        btn_refresh.setObjectName("primaryBtn")
        btn_refresh.clicked.connect(self.execute_log_query)
        top_bar.addWidget(btn_refresh)

        layout.addLayout(top_bar)

        # 3. Main Tabs: Log Explorer vs Maintenance & Disk Space
        tabs = QTabWidget()

        # Tab 1: Log Explorer
        tab_logs = QWidget()
        logs_layout = QVBoxLayout(tab_logs)
        logs_layout.setContentsMargins(6, 6, 6, 6)
        logs_layout.setSpacing(8)

        # Filter Controls Box
        filter_box = QGroupBox(tr("group_filters"))
        filter_grid = QGridLayout(filter_box)
        filter_grid.setSpacing(6)

        # Boot Session (-b)
        filter_grid.addWidget(QLabel(tr("lbl_boot")), 0, 0)
        self.cmb_boot = QComboBox()
        self.cmb_boot.setToolTip(format_tooltip(
            tr("tooltip_boot_title"),
            tr("tooltip_boot_syntax"),
            tr("tooltip_boot_desc"),
            tr("tooltip_boot_impact"),
            tr("tooltip_boot_example"),
        ))
        self.cmb_boot.currentIndexChanged.connect(self._on_filter_changed)
        filter_grid.addWidget(self.cmb_boot, 0, 1)

        # Priority Level (-p)
        filter_grid.addWidget(QLabel(tr("lbl_priority")), 0, 2)
        self.cmb_priority = QComboBox()
        for p_val, label, desc in PRIORITY_LEVELS:
            self.cmb_priority.addItem(label, p_val)
        self.cmb_priority.setCurrentIndex(1)  # Default: warning..emerg
        self.cmb_priority.currentIndexChanged.connect(self._on_filter_changed)
        filter_grid.addWidget(self.cmb_priority, 0, 3)

        # Service Unit (-u)
        filter_grid.addWidget(QLabel(tr("lbl_service_unit")), 1, 0)
        self.txt_unit = QLineEdit()
        self.txt_unit.setPlaceholderText(tr("placeholder_unit"))
        self.txt_unit.setToolTip(format_tooltip(
            tr("tooltip_unit_title"),
            tr("tooltip_unit_syntax"),
            tr("tooltip_unit_desc"),
            tr("tooltip_unit_impact"),
            tr("tooltip_unit_example"),
        ))
        self.txt_unit.textChanged.connect(self._on_filter_changed)
        filter_grid.addWidget(self.txt_unit, 1, 1)

        # Text search (-g)
        filter_grid.addWidget(QLabel(tr("lbl_search_pattern")), 1, 2)
        self.txt_grep = QLineEdit()
        self.txt_grep.setPlaceholderText(tr("placeholder_grep"))
        self.txt_grep.setToolTip(format_tooltip(
            tr("tooltip_grep_title"),
            tr("tooltip_grep_syntax"),
            tr("tooltip_grep_desc"),
            tr("tooltip_grep_impact"),
        ))
        self.txt_grep.textChanged.connect(self._on_filter_changed)
        filter_grid.addWidget(self.txt_grep, 1, 3)

        # Number of lines (-n)
        filter_grid.addWidget(QLabel(tr("lbl_line_limit")), 2, 0)
        self.spn_lines = QSpinBox()
        self.spn_lines.setRange(20, 5000)
        self.spn_lines.setValue(200)
        self.spn_lines.setSingleStep(50)
        self.spn_lines.setToolTip(format_tooltip(tr("tooltip_lines_title"), tr("tooltip_lines_syntax"), tr("tooltip_lines_desc")))
        self.spn_lines.valueChanged.connect(self._on_filter_changed)
        filter_grid.addWidget(self.spn_lines, 2, 1)

        btn_run = QPushButton(tr("btn_apply_filters"))
        btn_run.clicked.connect(self.execute_log_query)
        filter_grid.addWidget(btn_run, 2, 2, 1, 2)

        logs_layout.addWidget(filter_box)

        # Monospace Log Output Box
        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        mono_font = QFont("JetBrains Mono", 10)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        self.txt_logs.setFont(mono_font)
        self.txt_logs.setStyleSheet("background-color: #18191c; color: #e3e5e8; border: 1px solid #3a3d45; border-radius: 3px; padding: 6px;")
        logs_layout.addWidget(self.txt_logs)

        # Bottom Log Controls
        log_bar = QHBoxLayout()
        log_bar.setSpacing(8)
        self.lbl_status = QLabel(tr("lbl_status_ready"))
        self.lbl_status.setStyleSheet("color: #6899e6; font-weight: bold;")
        log_bar.addWidget(self.lbl_status)

        log_bar.addStretch()

        btn_copy = QPushButton(tr("btn_copy_logs"))
        btn_copy.clicked.connect(self._copy_logs)
        log_bar.addWidget(btn_copy)

        btn_export = QPushButton(tr("btn_export_logs"))
        btn_export.clicked.connect(self._export_logs)
        log_bar.addWidget(btn_export)

        logs_layout.addLayout(log_bar)
        tabs.addTab(tab_logs, tr("tab_logs"))

        # Tab 2: Maintenance & Disk Cleanup
        tab_maint = QWidget()
        maint_layout = QVBoxLayout(tab_maint)
        maint_layout.setContentsMargins(10, 10, 10, 10)
        maint_layout.setSpacing(8)

        # Disk usage card
        usage_card = QGroupBox(tr("group_usage"))
        usage_card_layout = QVBoxLayout(usage_card)
        usage_card_layout.setSpacing(6)
        self.lbl_disk_usage = QLabel(tr("lbl_usage_calc"))
        self.lbl_disk_usage.setStyleSheet("font-size: 14px; font-weight: bold; color: #6899e6; padding: 4px;")
        usage_card_layout.addWidget(self.lbl_disk_usage)

        lbl_usage_desc = QLabel(tr("lbl_usage_desc"))
        lbl_usage_desc.setWordWrap(True)
        lbl_usage_desc.setStyleSheet("color: #9498a1; font-size: 11px;")
        usage_card_layout.addWidget(lbl_usage_desc)
        maint_layout.addWidget(usage_card)

        # Vacuum by time
        time_box = QGroupBox(tr("group_vacuum_time"))
        time_layout = QGridLayout(time_box)
        time_layout.setSpacing(8)

        btn_vac_7d = QPushButton(tr("btn_vac_7d"))
        btn_vac_7d.setToolTip(format_tooltip(tr("tooltip_vac_time_title"), tr("tooltip_vac_time_syntax"), tr("tooltip_vac_time_desc"), tr("tooltip_vac_time_impact")))
        btn_vac_7d.clicked.connect(lambda: self._run_vacuum("--vacuum-time=7d"))
        time_layout.addWidget(btn_vac_7d, 0, 0)

        btn_vac_14d = QPushButton(tr("btn_vac_14d"))
        btn_vac_14d.clicked.connect(lambda: self._run_vacuum("--vacuum-time=14d"))
        time_layout.addWidget(btn_vac_14d, 0, 1)

        btn_vac_30d = QPushButton(tr("btn_vac_30d"))
        btn_vac_30d.clicked.connect(lambda: self._run_vacuum("--vacuum-time=30d"))
        time_layout.addWidget(btn_vac_30d, 1, 0)

        btn_vac_custom_time = QPushButton(tr("btn_vac_custom_time"))
        btn_vac_custom_time.clicked.connect(self._custom_vacuum_time)
        time_layout.addWidget(btn_vac_custom_time, 1, 1)
        maint_layout.addWidget(time_box)

        # Vacuum by size
        size_box = QGroupBox(tr("group_vacuum_size"))
        size_layout = QGridLayout(size_box)
        size_layout.setSpacing(8)

        btn_vac_200m = QPushButton(tr("btn_vac_200m"))
        btn_vac_200m.clicked.connect(lambda: self._run_vacuum("--vacuum-size=200M"))
        size_layout.addWidget(btn_vac_200m, 0, 0)

        btn_vac_500m = QPushButton(tr("btn_vac_500m"))
        btn_vac_500m.clicked.connect(lambda: self._run_vacuum("--vacuum-size=500M"))
        size_layout.addWidget(btn_vac_500m, 0, 1)

        btn_vac_1g = QPushButton(tr("btn_vac_1g"))
        btn_vac_1g.clicked.connect(lambda: self._run_vacuum("--vacuum-size=1G"))
        size_layout.addWidget(btn_vac_1g, 1, 0)

        btn_vac_custom_sz = QPushButton(tr("btn_vac_custom_sz"))
        btn_vac_custom_sz.clicked.connect(self._custom_vacuum_size)
        size_layout.addWidget(btn_vac_custom_sz, 1, 1)
        maint_layout.addWidget(size_box)

        maint_layout.addStretch()
        tabs.addTab(tab_maint, tr("tab_maint"))

        layout.addWidget(tabs)
        self._refresh_disk_usage()

    def _load_boot_sessions(self) -> None:
        self.cmb_boot.clear()
        self.cmb_boot.addItem(tr("opt_current_boot"), "0")
        self.cmb_boot.addItem(tr("opt_prev_boot"), "-1")
        for offset, label in JournalBackend.list_boot_sessions():
            if offset not in ("0", "-1"):
                self.cmb_boot.addItem(label, offset)
        self.cmb_boot.addItem(tr("opt_all_boot"), "all")

    def _on_filter_changed(self) -> None:
        boot = self.cmb_boot.currentData() or "0"
        unit = self.txt_unit.text().strip()
        priority = self.cmb_priority.currentData() or "warning"
        grep = self.txt_grep.text().strip()
        lines = self.spn_lines.value()
        user_mode = self.rb_user.isChecked()

        cmd = JournalBackend.build_query_cmd(boot, unit, priority, grep, lines, user_mode)
        self.preview_banner.set_text(" ".join(cmd))

    def execute_log_query(self) -> None:
        boot = self.cmb_boot.currentData() or "0"
        unit = self.txt_unit.text().strip()
        priority = self.cmb_priority.currentData() or "warning"
        grep = self.txt_grep.text().strip()
        lines = self.spn_lines.value()
        user_mode = self.rb_user.isChecked()

        cmd_str, raw_output = JournalBackend.fetch_logs(boot, unit, priority, grep, lines, user_mode)
        self.preview_banner.set_text(cmd_str)

        # Colorize output
        self._render_colorized_logs(raw_output)
        line_count = len(raw_output.splitlines())
        self.lbl_status.setText(tr("lbl_status_showing", count=line_count))

    def _render_colorized_logs(self, text: str) -> None:
        html_lines = []
        for line in text.splitlines():
            escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            low = line.lower()
            if "error" in low or "failed" in low or "emerg" in low or "crit" in low:
                html_lines.append(f"<span style='color: #e5534b;'>{escaped}</span>")
            elif "warn" in low:
                html_lines.append(f"<span style='color: #e3b341;'>{escaped}</span>")
            elif "started" in low or "reached" in low or "success" in low:
                html_lines.append(f"<span style='color: #57ab5a;'>{escaped}</span>")
            else:
                html_lines.append(f"<span style='color: #e3e5e8;'>{escaped}</span>")
        self.txt_logs.setHtml(f"<pre style='font-family: monospace; line-height: 1.3;'>{'<br>'.join(html_lines)}</pre>")

    def _refresh_disk_usage(self) -> None:
        usage = JournalBackend.get_disk_usage()
        self.lbl_disk_usage.setText(f"💾 {usage}")

    def _copy_logs(self) -> None:
        from PyQt6.QtGui import QGuiApplication
        clip = QGuiApplication.clipboard()
        if clip:
            clip.setText(self.txt_logs.toPlainText())
            QMessageBox.information(self, tr("title_copied"), tr("msg_copied"))

    def _export_logs(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, tr("dialog_save_logs_title"), "system_journal.log", tr("dialog_save_logs_filter"))
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.txt_logs.toPlainText())
            QMessageBox.information(self, tr("title_exported"), tr("msg_exported", path=path))

    def _run_vacuum(self, vacuum_arg: str) -> None:
        cmd_str = f"sudo journalctl {vacuum_arg}"
        self.preview_banner.set_text(cmd_str)

        dlg = SafetyExecutionDialog(
            title=tr("dialog_confirm_vacuum_title"),
            target_path_or_command=cmd_str,
            safety_notes=[
                tr("note_vacuum_purge"),
                tr("note_vacuum_active_safe"),
                tr("note_vacuum_root"),
            ],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = JournalBackend.execute_vacuum(vacuum_arg)
            if res.success:
                QMessageBox.information(self, tr("title_vacuum_completed"), tr("msg_vacuum_completed", output=res.stdout))
                self._refresh_disk_usage()
            else:
                QMessageBox.critical(self, tr("title_vacuum_failed"), tr("msg_vacuum_failed", error=res.stderr or res.stdout))

    def _custom_vacuum_time(self) -> None:
        from PyQt6.QtWidgets import QInputDialog
        val, ok = QInputDialog.getText(self, tr("dialog_custom_age_title"), tr("dialog_custom_age_label"))
        if ok and val.strip():
            self._run_vacuum(f"--vacuum-time={val.strip()}")

    def _custom_vacuum_size(self) -> None:
        from PyQt6.QtWidgets import QInputDialog
        val, ok = QInputDialog.getText(self, tr("dialog_custom_size_title"), tr("dialog_custom_size_label"))
        if ok and val.strip():
            self._run_vacuum(f"--vacuum-size={val.strip()}")
