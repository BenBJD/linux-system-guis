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
from systemd_gui.strings import tr


class SystemdMainWindow(QMainWindow):
    """Main window for managing systemd services and timers."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("window_title"))
        self.resize(1280, 720)
        self.setMinimumSize(920, 620)

        self.user_mode: bool = False
        self.selected_service: str = ""
        self.selected_timer: str = ""

        self._init_ui()
        self.refresh_all()

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

        # 2. Scope Switcher (System vs User)
        scope_bar = QHBoxLayout()
        scope_bar.setSpacing(8)
        scope_bar.addWidget(QLabel(tr("lbl_target_scope")))
        self.rb_system = QRadioButton(tr("rb_system"))
        self.rb_system.setChecked(True)
        self.rb_system.toggled.connect(self._on_scope_changed)
        scope_bar.addWidget(self.rb_system)

        self.rb_user = QRadioButton(tr("rb_user"))
        self.rb_user.toggled.connect(self._on_scope_changed)
        scope_bar.addWidget(self.rb_user)

        scope_bar.addStretch()

        btn_daemon_reload = QPushButton(tr("btn_daemon_reload"))
        btn_daemon_reload.setToolTip(format_tooltip(
            tr("tooltip_daemon_reload_title"),
            tr("tooltip_daemon_reload_cmd"),
            tr("tooltip_daemon_reload_desc"),
            tr("tooltip_daemon_reload_safety"),
        ))
        btn_daemon_reload.clicked.connect(self._do_daemon_reload)
        scope_bar.addWidget(btn_daemon_reload)

        btn_refresh = QPushButton(tr("btn_refresh"))
        btn_refresh.clicked.connect(self.refresh_all)
        scope_bar.addWidget(btn_refresh)

        layout.addLayout(scope_bar)

        # 3. Tabs: Services vs Timers
        tabs = QTabWidget()

        # Tab 1: Services
        svc_tab = QWidget()
        svc_layout = QVBoxLayout(svc_tab)
        svc_layout.setContentsMargins(6, 6, 6, 6)
        svc_layout.setSpacing(8)

        # Filter bar
        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel(tr("lbl_filter_services")))
        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText(tr("placeholder_filter_services"))
        self.txt_filter.textChanged.connect(self._filter_services)
        filter_bar.addWidget(self.txt_filter)
        svc_layout.addLayout(filter_bar)

        svc_splitter = QSplitter(Qt.Orientation.Vertical)

        self.tbl_services = QTableWidget(0, 4)
        self.tbl_services.setHorizontalHeaderLabels([
            tr("col_svc_name"),
            tr("col_svc_state"),
            tr("col_svc_boot"),
            tr("col_svc_desc"),
        ])
        self.tbl_services.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tbl_services.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.tbl_services.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.tbl_services.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tbl_services.setColumnWidth(0, 240)
        self.tbl_services.setColumnWidth(1, 170)
        self.tbl_services.setColumnWidth(2, 200)
        self.tbl_services.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_services.itemSelectionChanged.connect(self._on_service_selected)
        svc_splitter.addWidget(self.tbl_services)

        # Service Details & Control panel
        svc_control = QWidget()
        svc_control_layout = QVBoxLayout(svc_control)
        svc_control_layout.setContentsMargins(0, 6, 0, 0)
        svc_control_layout.setSpacing(6)

        # Status summary badge
        self.lbl_svc_summary = QLabel(tr("lbl_select_svc"))
        self.lbl_svc_summary.setStyleSheet("font-size: 12px; font-weight: bold; color: #6899e6; padding: 2px;")
        svc_control_layout.addWidget(self.lbl_svc_summary)

        self.txt_status = QTextEdit()
        self.txt_status.setReadOnly(True)
        self.txt_status.setStyleSheet("background-color: #18191c; color: #e3e5e8; font-family: monospace; font-size: 11px;")
        svc_control_layout.addWidget(self.txt_status)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.btn_start = QPushButton(tr("btn_start"))
        self.btn_start.setToolTip(format_tooltip(
            tr("tooltip_start_title"),
            tr("tooltip_start_cmd"),
            tr("tooltip_start_desc"),
            tr("tooltip_start_impact"),
        ))
        self.btn_start.clicked.connect(lambda: self._execute_service_action("start"))
        btn_row.addWidget(self.btn_start)

        self.btn_stop = QPushButton(tr("btn_stop"))
        self.btn_stop.setToolTip(format_tooltip(
            tr("tooltip_stop_title"),
            tr("tooltip_stop_cmd"),
            tr("tooltip_stop_desc"),
            tr("tooltip_stop_impact"),
        ))
        self.btn_stop.clicked.connect(lambda: self._execute_service_action("stop"))
        btn_row.addWidget(self.btn_stop)

        self.btn_restart = QPushButton(tr("btn_restart"))
        self.btn_restart.setToolTip(format_tooltip(
            tr("tooltip_restart_title"),
            tr("tooltip_restart_cmd"),
            tr("tooltip_restart_desc"),
            tr("tooltip_restart_impact"),
        ))
        self.btn_restart.clicked.connect(lambda: self._execute_service_action("restart"))
        btn_row.addWidget(self.btn_restart)

        self.btn_enable_now = QPushButton(tr("btn_enable_now"))
        self.btn_enable_now.setObjectName("primaryBtn")
        self.btn_enable_now.setToolTip(format_tooltip(
            tr("tooltip_enable_now_title"),
            tr("tooltip_enable_now_cmd"),
            tr("tooltip_enable_now_desc"),
            tr("tooltip_enable_now_impact"),
        ))
        self.btn_enable_now.clicked.connect(lambda: self._execute_service_action("enable --now"))
        btn_row.addWidget(self.btn_enable_now)

        self.btn_disable = QPushButton(tr("btn_disable"))
        self.btn_disable.setToolTip(format_tooltip(
            tr("tooltip_disable_title"),
            tr("tooltip_disable_cmd"),
            tr("tooltip_disable_desc"),
            tr("tooltip_disable_impact"),
        ))
        self.btn_disable.clicked.connect(lambda: self._execute_service_action("disable"))
        btn_row.addWidget(self.btn_disable)

        svc_control_layout.addLayout(btn_row)
        svc_splitter.addWidget(svc_control)
        svc_layout.addWidget(svc_splitter)
        tabs.addTab(svc_tab, tr("tab_services"))

        # Tab 2: Timers
        timer_tab = QWidget()
        timer_layout = QVBoxLayout(timer_tab)
        timer_layout.setContentsMargins(6, 6, 6, 6)
        timer_layout.setSpacing(8)

        timer_splitter = QSplitter(Qt.Orientation.Vertical)

        self.tbl_timers = QTableWidget(0, 4)
        self.tbl_timers.setHorizontalHeaderLabels([
            tr("col_timer_next"),
            tr("col_timer_left"),
            tr("col_timer_unit"),
            tr("col_timer_activates"),
        ])
        self.tbl_timers.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tbl_timers.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.tbl_timers.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.tbl_timers.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tbl_timers.setColumnWidth(0, 200)
        self.tbl_timers.setColumnWidth(1, 130)
        self.tbl_timers.setColumnWidth(2, 240)
        self.tbl_timers.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_timers.itemSelectionChanged.connect(self._on_timer_selected)
        timer_splitter.addWidget(self.tbl_timers)

        # Timer Generator Box
        gen_box = QGroupBox(tr("group_create_timer"))
        gen_grid = QGridLayout(gen_box)
        gen_grid.setSpacing(8)

        gen_grid.addWidget(QLabel(tr("lbl_timer_name")), 0, 0)
        self.txt_timer_name = QLineEdit("backup-task.timer")
        self.txt_timer_name.textChanged.connect(self._update_timer_preview)
        gen_grid.addWidget(self.txt_timer_name, 0, 1)

        gen_grid.addWidget(QLabel(tr("lbl_schedule")), 0, 2)
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
            tr("tooltip_schedule_title"),
            tr("tooltip_schedule_syntax"),
            tr("tooltip_schedule_desc"),
            tr("tooltip_schedule_impact"),
            tr("tooltip_schedule_example"),
        ))
        self.cmb_schedule.currentTextChanged.connect(self._update_timer_preview)
        gen_grid.addWidget(self.cmb_schedule, 0, 3)

        self.chk_persistent = QCheckBox(tr("chk_persistent"))
        self.chk_persistent.setChecked(True)
        self.chk_persistent.setToolTip(format_tooltip(
            tr("tooltip_persistent_title"),
            tr("tooltip_persistent_syntax"),
            tr("tooltip_persistent_desc"),
            tr("tooltip_persistent_impact"),
        ))
        self.chk_persistent.toggled.connect(self._update_timer_preview)
        gen_grid.addWidget(self.chk_persistent, 1, 0, 1, 2)

        timer_splitter.addWidget(gen_box)
        timer_layout.addWidget(timer_splitter)
        tabs.addTab(timer_tab, tr("tab_timers"))

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
            tr(
                "lbl_svc_summary",
                name=svc.name,
                status=svc.friendly_status,
                boot=svc.friendly_boot,
            )
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
            QMessageBox.warning(self, tr("title_no_service_selected"), tr("msg_select_service_first"))
            return

        cmd_str = SystemdManager.build_command_str(action, self.selected_service, self.user_mode)
        self.preview_banner.set_text(cmd_str)

        dlg = SafetyExecutionDialog(
            title=tr("dialog_exec_title", action=action),
            target_path_or_command=cmd_str,
            safety_notes=[
                tr("note_modifies_service", service=self.selected_service),
                tr("note_elevates_scope"),
            ],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = SystemdManager.execute_unit_action(action, self.selected_service, self.user_mode)
            if res.success:
                QMessageBox.information(self, tr("title_success"), tr("msg_exec_success", command=cmd_str))
                self._load_services()
                self._on_service_selected()
            else:
                QMessageBox.critical(self, tr("title_action_failed"), tr("msg_action_failed", error=res.stderr or res.stdout))

    def _do_daemon_reload(self) -> None:
        cmd_str = "systemctl --user daemon-reload" if self.user_mode else "sudo systemctl daemon-reload"
        self.preview_banner.set_text(cmd_str)
        dlg = SafetyExecutionDialog(
            title=tr("dialog_daemon_reload_title"),
            target_path_or_command=cmd_str,
            safety_notes=[tr("note_reload_configs")],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = SystemdManager.execute_unit_action("daemon-reload", "", self.user_mode)
            if res.success:
                QMessageBox.information(self, tr("title_reloaded"), tr("msg_daemon_reload_success"))
            else:
                QMessageBox.critical(self, tr("title_error"), tr("msg_daemon_reload_failed", error=res.stderr))
