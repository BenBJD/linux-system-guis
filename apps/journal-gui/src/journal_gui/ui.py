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
        self.setWindowTitle("System Journal & Log Explorer (journalctl)")
        self.resize(1180, 820)
        self.setMinimumSize(960, 680)

        self._init_ui()
        self._load_boot_sessions()
        self.execute_log_query()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Top Live Preview Banner
        self.preview_banner = LivePreviewBanner(
            title="Journalctl Command Preview",
            subtitle="Modifying dropdowns and filters below immediately constructs the exact terminal command.",
        )
        layout.addWidget(self.preview_banner)

        # 2. Scope & Quick Bar
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Scope:"))
        self.rb_system = QRadioButton("System Logs (All Daemons & Kernel)")
        self.rb_system.setChecked(True)
        self.rb_system.toggled.connect(self._on_filter_changed)
        top_bar.addWidget(self.rb_system)

        self.rb_user = QRadioButton("User Session (--user)")
        self.rb_user.toggled.connect(self._on_filter_changed)
        top_bar.addWidget(self.rb_user)

        top_bar.addStretch()

        btn_refresh = QPushButton("🔃 Refresh Logs")
        btn_refresh.setObjectName("primaryBtn")
        btn_refresh.clicked.connect(self.execute_log_query)
        top_bar.addWidget(btn_refresh)

        layout.addLayout(top_bar)

        # 3. Main Tabs: Log Explorer vs Maintenance & Disk Space
        tabs = QTabWidget()

        # Tab 1: Log Explorer
        tab_logs = QWidget()
        logs_layout = QVBoxLayout(tab_logs)
        logs_layout.setContentsMargins(8, 8, 8, 8)
        logs_layout.setSpacing(10)

        # Filter Controls Box
        filter_box = QGroupBox("Filter Criteria (Narrow down your logs)")
        filter_grid = QGridLayout(filter_box)
        filter_grid.setSpacing(8)

        # Boot Session (-b)
        filter_grid.addWidget(QLabel("Boot Session (-b):"), 0, 0)
        self.cmb_boot = QComboBox()
        self.cmb_boot.setToolTip(format_tooltip(
            "Boot Session Filter",
            "-b 0 or -b -1",
            "Limits logs to a specific boot. '0' is the current running system session, '-1' is the previous boot before the last restart.",
            "Standard: 0",
            "journalctl -b -1 (check why PC crashed on last boot)",
        ))
        self.cmb_boot.currentIndexChanged.connect(self._on_filter_changed)
        filter_grid.addWidget(self.cmb_boot, 0, 1)

        # Priority Level (-p)
        filter_grid.addWidget(QLabel("Log Priority (-p):"), 0, 2)
        self.cmb_priority = QComboBox()
        for p_val, label, desc in PRIORITY_LEVELS:
            self.cmb_priority.addItem(label, p_val)
        self.cmb_priority.setCurrentIndex(1)  # Default: warning..emerg
        self.cmb_priority.currentIndexChanged.connect(self._on_filter_changed)
        filter_grid.addWidget(self.cmb_priority, 0, 3)

        # Service Unit (-u)
        filter_grid.addWidget(QLabel("Service Unit (-u):"), 1, 0)
        self.txt_unit = QLineEdit()
        self.txt_unit.setPlaceholderText("e.g. NetworkManager.service, sshd.service, bluetooth.service")
        self.txt_unit.setToolTip(format_tooltip(
            "Service Filter",
            "-u <service_name>",
            "Isolates logs produced by a single systemd service unit. Leave blank to view all system activity.",
            "Safe",
            "journalctl -u docker.service",
        ))
        self.txt_unit.textChanged.connect(self._on_filter_changed)
        filter_grid.addWidget(self.txt_unit, 1, 1)

        # Text search (-g)
        filter_grid.addWidget(QLabel("Search Pattern (-g):"), 1, 2)
        self.txt_grep = QLineEdit()
        self.txt_grep.setPlaceholderText("Filter text string (e.g. failed, disconnect, timeout)...")
        self.txt_grep.setToolTip(format_tooltip(
            "Pattern Match",
            "-g <pattern>",
            "Regular expression or substring filter for journal messages.",
            "Safe",
        ))
        self.txt_grep.textChanged.connect(self._on_filter_changed)
        filter_grid.addWidget(self.txt_grep, 1, 3)

        # Number of lines (-n)
        filter_grid.addWidget(QLabel("Line Limit (-n):"), 2, 0)
        self.spn_lines = QSpinBox()
        self.spn_lines.setRange(20, 5000)
        self.spn_lines.setValue(200)
        self.spn_lines.setSingleStep(50)
        self.spn_lines.setToolTip(format_tooltip("Entry Limit", "-n <count>", "Controls how many recent entries to display."))
        self.spn_lines.valueChanged.connect(self._on_filter_changed)
        filter_grid.addWidget(self.spn_lines, 2, 1)

        btn_run = QPushButton("🔍 Apply Filters && Search")
        btn_run.clicked.connect(self.execute_log_query)
        filter_grid.addWidget(btn_run, 2, 2, 1, 2)

        logs_layout.addWidget(filter_box)

        # Monospace Log Output Box
        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        mono_font = QFont("JetBrains Mono", 10)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        self.txt_logs.setFont(mono_font)
        self.txt_logs.setStyleSheet("background-color: #11111b; color: #cdd6f4; border: 1px solid #313244; border-radius: 8px; padding: 6px;")
        logs_layout.addWidget(self.txt_logs)

        # Bottom Log Controls
        log_bar = QHBoxLayout()
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setStyleSheet("color: #89b4fa; font-weight: bold;")
        log_bar.addWidget(self.lbl_status)

        log_bar.addStretch()

        btn_copy = QPushButton("📋 Copy Visible Logs")
        btn_copy.clicked.connect(self._copy_logs)
        log_bar.addWidget(btn_copy)

        btn_export = QPushButton("💾 Export to .log File")
        btn_export.clicked.connect(self._export_logs)
        log_bar.addWidget(btn_export)

        logs_layout.addLayout(log_bar)
        tabs.addTab(tab_logs, "📜 Log Explorer")

        # Tab 2: Maintenance & Disk Cleanup
        tab_maint = QWidget()
        maint_layout = QVBoxLayout(tab_maint)
        maint_layout.setContentsMargins(16, 16, 16, 16)
        maint_layout.setSpacing(14)

        # Disk usage card
        usage_card = QGroupBox("Current Journal Disk Usage")
        usage_card_layout = QVBoxLayout(usage_card)
        self.lbl_disk_usage = QLabel("Calculating journal disk usage...")
        self.lbl_disk_usage.setStyleSheet("font-size: 15px; font-weight: bold; color: #89b4fa; padding: 6px;")
        usage_card_layout.addWidget(self.lbl_disk_usage)

        lbl_usage_desc = QLabel(
            "Systemd stores system logs under /var/log/journal. Over months, archived logs can consume multiple gigabytes "
            "of disk space. You can safely vacuum old logs without affecting system stability."
        )
        lbl_usage_desc.setWordWrap(True)
        lbl_usage_desc.setStyleSheet("color: #a6adc8; font-size: 12px;")
        usage_card_layout.addWidget(lbl_usage_desc)
        maint_layout.addWidget(usage_card)

        # Vacuum by time
        time_box = QGroupBox("Cleanup by Retention Age (--vacuum-time)")
        time_layout = QGridLayout(time_box)
        time_layout.setSpacing(10)

        btn_vac_7d = QPushButton("🧹 Vacuum older than 7 Days (--vacuum-time=7d)")
        btn_vac_7d.setToolTip(format_tooltip("Vacuum by Time", "journalctl --vacuum-time=7d", "Deletes archived logs older than 7 days.", "Safe / Recommended"))
        btn_vac_7d.clicked.connect(lambda: self._run_vacuum("--vacuum-time=7d"))
        time_layout.addWidget(btn_vac_7d, 0, 0)

        btn_vac_14d = QPushButton("🧹 Vacuum older than 2 Weeks (--vacuum-time=14d)")
        btn_vac_14d.clicked.connect(lambda: self._run_vacuum("--vacuum-time=14d"))
        time_layout.addWidget(btn_vac_14d, 0, 1)

        btn_vac_30d = QPushButton("🧹 Vacuum older than 1 Month (--vacuum-time=30d)")
        btn_vac_30d.clicked.connect(lambda: self._run_vacuum("--vacuum-time=30d"))
        time_layout.addWidget(btn_vac_30d, 1, 0)

        btn_vac_custom_time = QPushButton("🧹 Custom Age Vacuum...")
        btn_vac_custom_time.clicked.connect(self._custom_vacuum_time)
        time_layout.addWidget(btn_vac_custom_time, 1, 1)
        maint_layout.addWidget(time_box)

        # Vacuum by size
        size_box = QGroupBox("Cleanup by Maximum Disk Size (--vacuum-size)")
        size_layout = QGridLayout(size_box)
        size_layout.setSpacing(10)

        btn_vac_200m = QPushButton("📦 Vacuum to max 200 MB (--vacuum-size=200M)")
        btn_vac_200m.clicked.connect(lambda: self._run_vacuum("--vacuum-size=200M"))
        size_layout.addWidget(btn_vac_200m, 0, 0)

        btn_vac_500m = QPushButton("📦 Vacuum to max 500 MB (--vacuum-size=500M)")
        btn_vac_500m.clicked.connect(lambda: self._run_vacuum("--vacuum-size=500M"))
        size_layout.addWidget(btn_vac_500m, 0, 1)

        btn_vac_1g = QPushButton("📦 Vacuum to max 1 GB (--vacuum-size=1G)")
        btn_vac_1g.clicked.connect(lambda: self._run_vacuum("--vacuum-size=1G"))
        size_layout.addWidget(btn_vac_1g, 1, 0)

        btn_vac_custom_sz = QPushButton("📦 Custom Size Vacuum...")
        btn_vac_custom_sz.clicked.connect(self._custom_vacuum_size)
        size_layout.addWidget(btn_vac_custom_sz, 1, 1)
        maint_layout.addWidget(size_box)

        maint_layout.addStretch()
        tabs.addTab(tab_maint, "🧹 Maintenance & Disk Cleanup")

        layout.addWidget(tabs)
        self._refresh_disk_usage()

    def _load_boot_sessions(self) -> None:
        self.cmb_boot.clear()
        self.cmb_boot.addItem("Current Boot (0)", "0")
        self.cmb_boot.addItem("Previous Boot (-1)", "-1")
        for offset, label in JournalBackend.list_boot_sessions():
            if offset not in ("0", "-1"):
                self.cmb_boot.addItem(label, offset)
        self.cmb_boot.addItem("All Boot History", "all")

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
        self.lbl_status.setText(f"Showing {line_count} log entries")

    def _render_colorized_logs(self, text: str) -> None:
        html_lines = []
        for line in text.splitlines():
            escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            low = line.lower()
            if "error" in low or "failed" in low or "emerg" in low or "crit" in low:
                html_lines.append(f"<span style='color: #f38ba8;'>{escaped}</span>")
            elif "warn" in low:
                html_lines.append(f"<span style='color: #f9e2af;'>{escaped}</span>")
            elif "started" in low or "reached" in low or "success" in low:
                html_lines.append(f"<span style='color: #a6e3a1;'>{escaped}</span>")
            else:
                html_lines.append(f"<span style='color: #cdd6f4;'>{escaped}</span>")
        self.txt_logs.setHtml(f"<pre style='font-family: monospace; line-height: 1.3;'>{'<br>'.join(html_lines)}</pre>")

    def _refresh_disk_usage(self) -> None:
        usage = JournalBackend.get_disk_usage()
        self.lbl_disk_usage.setText(f"💾 {usage}")

    def _copy_logs(self) -> None:
        from PyQt6.QtGui import QGuiApplication
        clip = QGuiApplication.clipboard()
        if clip:
            clip.setText(self.txt_logs.toPlainText())
            QMessageBox.information(self, "Copied", "Visible log entries copied to clipboard.")

    def _export_logs(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save Journal Logs", "system_journal.log", "Log Files (*.log);;All Files (*)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.txt_logs.toPlainText())
            QMessageBox.information(self, "Exported", f"Logs successfully saved to {path}")

    def _run_vacuum(self, vacuum_arg: str) -> None:
        cmd_str = f"sudo journalctl {vacuum_arg}"
        self.preview_banner.set_text(cmd_str)

        dlg = SafetyExecutionDialog(
            title="Confirm Journal Vacuum Maintenance",
            target_path_or_command=cmd_str,
            safety_notes=[
                "Safely purges old archived logs to free disk space.",
                "Active log entries from the current boot session are never deleted.",
                "Requires elevated root privileges.",
            ],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = JournalBackend.execute_vacuum(vacuum_arg)
            if res.success:
                QMessageBox.information(self, "Vacuum Completed", f"Vacuum finished!\n\n{res.stdout}")
                self._refresh_disk_usage()
            else:
                QMessageBox.critical(self, "Vacuum Failed", f"Failed:\n{res.stderr or res.stdout}")

    def _custom_vacuum_time(self) -> None:
        from PyQt6.QtWidgets import QInputDialog
        val, ok = QInputDialog.getText(self, "Custom Vacuum Age", "Enter retention threshold (e.g. 5d, 2weeks, 1month):")
        if ok and val.strip():
            self._run_vacuum(f"--vacuum-time={val.strip()}")

    def _custom_vacuum_size(self) -> None:
        from PyQt6.QtWidgets import QInputDialog
        val, ok = QInputDialog.getText(self, "Custom Vacuum Size", "Enter maximum journal size (e.g. 300M, 2G):")
        if ok and val.strip():
            self._run_vacuum(f"--vacuum-size={val.strip()}")
