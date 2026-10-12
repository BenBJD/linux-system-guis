"""User interface for systemd service and timer manager."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
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
    QRadioButton,
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
from systemd_gui.manager import ServiceUnit, SystemdManager, TimerUnit


class SystemdMainWindow(QMainWindow):
    """Main window for managing systemd services and timers."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("systemd Service & Timer Explorer")
        self.resize(1180, 820)
        self.setMinimumSize(960, 680)

        self.user_mode: bool = False
        self.selected_service: str = ""
        self.selected_timer: str = ""

        self._init_ui()
        self.refresh_all()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Top Live Preview Banner
        self.preview_banner = LivePreviewBanner(
            title="Systemctl Command Preview",
            subtitle="Shows the exact systemctl command and flags before execution. Hover over actions for safety tooltips.",
        )
        layout.addWidget(self.preview_banner)

        # 2. Scope Switcher (System vs User)
        scope_bar = QHBoxLayout()
        scope_bar.addWidget(QLabel("Target Scope:"))
        self.rb_system = QRadioButton("System Scope (/etc/systemd/system, requires root)")
        self.rb_system.setChecked(True)
        self.rb_system.toggled.connect(self._on_scope_changed)
        scope_bar.addWidget(self.rb_system)

        self.rb_user = QRadioButton("User Session (~/.config/systemd/user, rootless)")
        self.rb_user.toggled.connect(self._on_scope_changed)
        scope_bar.addWidget(self.rb_user)

        scope_bar.addStretch()

        btn_daemon_reload = QPushButton("daemon-reload")
        btn_daemon_reload.setToolTip(format_tooltip(
            "Reload systemd manager",
            "systemctl daemon-reload",
            "Rereads all generator and unit files. Run this after modifying any .service or .timer file.",
            "Safe / Required after edits",
        ))
        btn_daemon_reload.clicked.connect(self._do_daemon_reload)
        scope_bar.addWidget(btn_daemon_reload)

        btn_refresh = QPushButton("Refresh List")
        btn_refresh.clicked.connect(self.refresh_all)
        scope_bar.addWidget(btn_refresh)

        layout.addLayout(scope_bar)

        # 3. Tabs: Services vs Timers
        tabs = QTabWidget()

        # Tab 1: Services
        svc_tab = QWidget()
        svc_layout = QVBoxLayout(svc_tab)
        svc_layout.setContentsMargins(8, 8, 8, 8)
        svc_layout.setSpacing(10)

        # Filter bar
        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel("Filter Services:"))
        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("Search service name or description (e.g. bluetooth, ssh, docker)...")
        self.txt_filter.textChanged.connect(self._filter_services)
        filter_bar.addWidget(self.txt_filter)
        svc_layout.addLayout(filter_bar)

        svc_splitter = QSplitter(Qt.Orientation.Vertical)

        self.tbl_services = QTableWidget(0, 4)
        self.tbl_services.setHorizontalHeaderLabels([
            "Service Unit Name",
            "Current Running State",
            "Starts on Boot?",
            "Description",
        ])
        self.tbl_services.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tbl_services.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.tbl_services.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.tbl_services.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tbl_services.setColumnWidth(0, 260)
        self.tbl_services.setColumnWidth(1, 190)
        self.tbl_services.setColumnWidth(2, 220)
        self.tbl_services.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_services.itemSelectionChanged.connect(self._on_service_selected)
        svc_splitter.addWidget(self.tbl_services)

        # Service Details & Control panel
        svc_control = QWidget()
        svc_control_layout = QVBoxLayout(svc_control)
        svc_control_layout.setContentsMargins(0, 8, 0, 0)
        svc_control_layout.setSpacing(8)

        # Status summary badge
        self.lbl_svc_summary = QLabel("Select a service above to inspect status and run actions.")
        self.lbl_svc_summary.setStyleSheet("font-size: 13px; font-weight: bold; color: #89b4fa; padding: 4px;")
        svc_control_layout.addWidget(self.lbl_svc_summary)

        self.txt_status = QTextEdit()
        self.txt_status.setReadOnly(True)
        self.txt_status.setStyleSheet("background-color: #11111b; color: #cdd6f4; font-family: monospace; font-size: 11px;")
        svc_control_layout.addWidget(self.txt_status)

        # Action Buttons
        btn_row = QHBoxLayout()

        self.btn_start = QPushButton("Start Service")
        self.btn_start.setToolTip(format_tooltip("Start Service", "systemctl start <unit>", "Starts (activates) the service immediately.", "Standard operation"))
        self.btn_start.clicked.connect(lambda: self._execute_service_action("start"))
        btn_row.addWidget(self.btn_start)

        self.btn_stop = QPushButton("Stop Service")
        self.btn_stop.setToolTip(format_tooltip("Stop Service", "systemctl stop <unit>", "Stops (deactivates) the running service immediately.", "Standard operation"))
        self.btn_stop.clicked.connect(lambda: self._execute_service_action("stop"))
        btn_row.addWidget(self.btn_stop)

        self.btn_restart = QPushButton("Restart Service")
        self.btn_restart.setToolTip(format_tooltip("Restart Service", "systemctl restart <unit>", "Stops and immediately restarts the service. Useful after configuration changes.", "Standard operation"))
        self.btn_restart.clicked.connect(lambda: self._execute_service_action("restart"))
        btn_row.addWidget(self.btn_restart)

        self.btn_enable_now = QPushButton("Enable to Run on Boot")
        self.btn_enable_now.setObjectName("primaryBtn")
        self.btn_enable_now.setToolTip(format_tooltip("Enable with --now", "systemctl enable --now <unit>", "Configures systemd to start this service every time your computer boots AND starts it right away.", "Safe / Recommended"))
        self.btn_enable_now.clicked.connect(lambda: self._execute_service_action("enable --now"))
        btn_row.addWidget(self.btn_enable_now)

        self.btn_disable = QPushButton("Disable Boot Startup")
        self.btn_disable.setToolTip(format_tooltip("Disable Service", "systemctl disable <unit>", "Removes automatic startup on boot. Does not terminate the currently running process.", "Safe"))
        self.btn_disable.clicked.connect(lambda: self._execute_service_action("disable"))
        btn_row.addWidget(self.btn_disable)

        svc_control_layout.addLayout(btn_row)
        svc_splitter.addWidget(svc_control)
        svc_layout.addWidget(svc_splitter)
        tabs.addTab(svc_tab, "Services")

        # Tab 2: Timers
        timer_tab = QWidget()
        timer_layout = QVBoxLayout(timer_tab)
        timer_layout.setContentsMargins(8, 8, 8, 8)
        timer_layout.setSpacing(10)

        timer_splitter = QSplitter(Qt.Orientation.Vertical)

        self.tbl_timers = QTableWidget(0, 4)
        self.tbl_timers.setHorizontalHeaderLabels(["Next Scheduled Trigger", "Trigger In", "Timer Unit", "Activates Service"])
        self.tbl_timers.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tbl_timers.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.tbl_timers.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.tbl_timers.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tbl_timers.setColumnWidth(0, 220)
        self.tbl_timers.setColumnWidth(1, 140)
        self.tbl_timers.setColumnWidth(2, 260)
        self.tbl_timers.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_timers.itemSelectionChanged.connect(self._on_timer_selected)
        timer_splitter.addWidget(self.tbl_timers)

        # Timer Generator Box
        gen_box = QGroupBox("Create New Scheduled Timer (systemd Timer Builder)")
        gen_grid = QGridLayout(gen_box)
        gen_grid.setSpacing(10)

        gen_grid.addWidget(QLabel("Timer Unit Name:"), 0, 0)
        self.txt_timer_name = QLineEdit("backup-task.timer")
        self.txt_timer_name.textChanged.connect(self._update_timer_preview)
        gen_grid.addWidget(self.txt_timer_name, 0, 1)

        gen_grid.addWidget(QLabel("Schedule (OnCalendar):"), 0, 2)
        self.cmb_schedule = QComboBox()
        self.cmb_schedule.setEditable(True)
        self.cmb_schedule.addItems([
            "daily",
            "weekly",
            "hourly",
            "*-*-* 03:00:00",
            "Mon..Fri *-*-* 09:00:00",
        ])
        self.cmb_schedule.setToolTip(format_tooltip(
            "OnCalendar Format",
            "OnCalendar=daily",
            "Defines the calendar expression when the timer activates the associated service.",
            "Safe",
            "*-*-* 04:30:00 (every day at 4:30 AM)",
        ))
        self.cmb_schedule.currentTextChanged.connect(self._update_timer_preview)
        gen_grid.addWidget(self.cmb_schedule, 0, 3)

        self.chk_persistent = QCheckBox("Persistent=true (Run missed events immediately if computer was off/asleep)")
        self.chk_persistent.setChecked(True)
        self.chk_persistent.setToolTip(format_tooltip(
            "Persistent Trigger",
            "Persistent=true",
            "Ensures missed timers (due to suspended or turned-off PC) trigger as soon as the machine boots up.",
            "Recommended for backups",
        ))
        self.chk_persistent.toggled.connect(self._update_timer_preview)
        gen_grid.addWidget(self.chk_persistent, 1, 0, 1, 2)

        timer_splitter.addWidget(gen_box)
        timer_layout.addWidget(timer_splitter)
        tabs.addTab(timer_tab, "Timers & Scheduler")

        layout.addWidget(tabs)

    def _on_scope_changed(self) -> None:
        self.user_mode = self.rb_user.isChecked()
        self.refresh_all()

    def refresh_all(self) -> None:
        self._load_services()
        self._load_timers()

    def _load_services(self) -> None:
        self.tbl_services.setRowCount(0)
        services = SystemdManager.list_services(self.user_mode)
        row = 0
        for s in services:
            self.tbl_services.insertRow(row)
            self.tbl_services.setItem(row, 0, QTableWidgetItem(s.name))
            self.tbl_services.setItem(row, 1, QTableWidgetItem(s.friendly_status))
            self.tbl_services.setItem(row, 2, QTableWidgetItem(s.friendly_boot))
            self.tbl_services.setItem(row, 3, QTableWidgetItem(s.description))
            self.tbl_services.item(row, 0).setData(Qt.ItemDataRole.UserRole, s)
            row += 1

    def _load_timers(self) -> None:
        self.tbl_timers.setRowCount(0)
        timers = SystemdManager.list_timers(self.user_mode)
        row = 0
        for t in timers:
            self.tbl_timers.insertRow(row)
            self.tbl_timers.setItem(row, 0, QTableWidgetItem(t.next_elapse))
            self.tbl_timers.setItem(row, 1, QTableWidgetItem(t.left))
            self.tbl_timers.setItem(row, 2, QTableWidgetItem(t.unit))
            self.tbl_timers.setItem(row, 3, QTableWidgetItem(t.activates))
            self.tbl_timers.item(row, 0).setData(Qt.ItemDataRole.UserRole, t)
            row += 1

    def _filter_services(self, text: str) -> None:
        needle = text.lower()
        for row in range(self.tbl_services.rowCount()):
            item = self.tbl_services.item(row, 0)
            desc = self.tbl_services.item(row, 3)
            matches = (item and needle in item.text().lower()) or (desc and needle in desc.text().lower())
            self.tbl_services.setRowHidden(row, not matches)

    def _on_service_selected(self) -> None:
        selected = self.tbl_services.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        svc: ServiceUnit = self.tbl_services.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.selected_service = svc.name

        # Update summary banner
        self.lbl_svc_summary.setText(
            f"Service: <b>{svc.name}</b> &nbsp;|&nbsp; "
            f"State: <b>{svc.friendly_status}</b> &nbsp;|&nbsp; "
            f"Boot Startup: <b>{svc.friendly_boot}</b>"
        )

        # Update live preview banner
        cmd_preview = SystemdManager.build_command_str("status", svc.name, self.user_mode)
        self.preview_banner.set_text(cmd_preview)

        # Show status
        status_output = SystemdManager.get_unit_status(svc.name, self.user_mode)
        self.txt_status.setPlainText(status_output)

    def _on_timer_selected(self) -> None:
        selected = self.tbl_timers.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        timer: TimerUnit = self.tbl_timers.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.selected_timer = timer.unit
        cmd = SystemdManager.build_command_str("status", timer.unit, self.user_mode)
        self.preview_banner.set_text(cmd)

    def _update_timer_preview(self) -> None:
        name = self.txt_timer_name.text().strip()
        cal = self.cmb_schedule.currentText().strip()
        persistent = "true" if self.chk_persistent.isChecked() else "false"

        timer_unit_text = f"[Timer]\nOnCalendar={cal}\nPersistent={persistent}\n\n[Install]\nWantedBy=timers.target"
        self.preview_banner.set_text(timer_unit_text)

    def _execute_service_action(self, action: str) -> None:
        if not self.selected_service:
            QMessageBox.warning(self, "No Service Selected", "Please select a service from the list first.")
            return

        cmd_str = SystemdManager.build_command_str(action, self.selected_service, self.user_mode)
        self.preview_banner.set_text(cmd_str)

        dlg = SafetyExecutionDialog(
            title=f"Execute: {action}",
            target_path_or_command=cmd_str,
            safety_notes=[
                f"Modifies state of {self.selected_service}",
                "Elevates with pkexec/sudo if system scope",
            ],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = SystemdManager.execute_unit_action(action, self.selected_service, self.user_mode)
            if res.success:
                QMessageBox.information(self, "Success", f"Executed:\n{cmd_str}")
                self._load_services()
                self._on_service_selected()
            else:
                QMessageBox.critical(self, "Action Failed", f"Error:\n{res.stderr or res.stdout}")

    def _do_daemon_reload(self) -> None:
        cmd_str = "systemctl --user daemon-reload" if self.user_mode else "sudo systemctl daemon-reload"
        self.preview_banner.set_text(cmd_str)
        dlg = SafetyExecutionDialog(
            title="systemd daemon-reload",
            target_path_or_command=cmd_str,
            safety_notes=["Reloads all systemd configurations into memory."],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = SystemdManager.execute_unit_action("daemon-reload", "", self.user_mode)
            if res.success:
                QMessageBox.information(self, "Reloaded", "daemon-reload completed successfully.")
            else:
                QMessageBox.critical(self, "Error", f"Failed:\n{res.stderr}")
