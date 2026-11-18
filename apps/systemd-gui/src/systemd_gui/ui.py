"""User interface for systemd service and timer manager."""

import os
import re
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
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from linux_gui_core.widgets.loading_modal import run_with_loading_modal
from linux_gui_core.widgets.preview_banner import LivePreviewBanner
from linux_gui_core.widgets.safety_dialog import SafetyExecutionDialog
from linux_gui_core.widgets.tooltips import format_tooltip
from systemd_gui.manager import ServiceUnit, SystemdManager, TimerConfig, TimerUnit
from systemd_gui.strings import tr


class SystemdMainWindow(QMainWindow):
    """Main window for managing systemd services and timers."""

    MAN_PAGES = [
        "systemctl(1)",
        "systemd.service(5)",
        "systemd.timer(5)",
        "systemd.time(7)",
        "systemd.unit(5)",
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("window_title"))
        self.resize(1280, 760)
        self.setMinimumSize(940, 640)

        self.user_mode: bool = False
        self.selected_service: str = ""
        self.selected_timer: str = ""
        self.active_timer_config: TimerConfig = TimerConfig()
        self.creating_new_timer: bool = False
        self._is_updating_timer_ui: bool = False

        self._init_ui()
        self.refresh_all()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # 1. Top Live Preview Banner with Man Page links
        self.preview_banner = LivePreviewBanner(
            title=tr("preview_title"),
            subtitle=tr("preview_subtitle"),
            man_pages=self.MAN_PAGES,
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
            man_page="systemctl(1)",
        ))
        btn_daemon_reload.clicked.connect(self._do_daemon_reload)
        scope_bar.addWidget(btn_daemon_reload)

        btn_refresh = QPushButton(tr("btn_refresh"))
        btn_refresh.clicked.connect(self.refresh_all)
        scope_bar.addWidget(btn_refresh)

        layout.addLayout(scope_bar)

        # 3. Tabs: Services vs Timers
        self.tabs = QTabWidget()

        # ==================== Tab 1: Services ====================
        svc_tab = QWidget()
        svc_layout = QVBoxLayout(svc_tab)
        svc_layout.setContentsMargins(6, 6, 6, 6)
        svc_layout.setSpacing(8)

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

        svc_control = QWidget()
        svc_control_layout = QVBoxLayout(svc_control)
        svc_control_layout.setContentsMargins(0, 6, 0, 0)
        svc_control_layout.setSpacing(6)

        self.lbl_svc_summary = QLabel(tr("lbl_select_svc"))
        self.lbl_svc_summary.setStyleSheet("font-size: 12px; font-weight: bold; color: #6899e6; padding: 2px;")
        svc_control_layout.addWidget(self.lbl_svc_summary)

        self.txt_status = QTextEdit()
        self.txt_status.setReadOnly(True)
        self.txt_status.setStyleSheet(
            "background-color: #18191c; color: #e3e5e8; font-family: monospace; font-size: 11px;"
        )
        svc_control_layout.addWidget(self.txt_status)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.btn_start = QPushButton(tr("btn_start"))
        self.btn_start.setToolTip(format_tooltip(
            tr("tooltip_start_title"),
            tr("tooltip_start_cmd"),
            tr("tooltip_start_desc"),
            tr("tooltip_start_impact"),
            man_page="systemctl(1)",
        ))
        self.btn_start.clicked.connect(lambda: self._execute_service_action("start"))
        btn_row.addWidget(self.btn_start)

        self.btn_stop = QPushButton(tr("btn_stop"))
        self.btn_stop.setToolTip(format_tooltip(
            tr("tooltip_stop_title"),
            tr("tooltip_stop_cmd"),
            tr("tooltip_stop_desc"),
            tr("tooltip_stop_impact"),
            man_page="systemctl(1)",
        ))
        self.btn_stop.clicked.connect(lambda: self._execute_service_action("stop"))
        btn_row.addWidget(self.btn_stop)

        self.btn_restart = QPushButton(tr("btn_restart"))
        self.btn_restart.setToolTip(format_tooltip(
            tr("tooltip_restart_title"),
            tr("tooltip_restart_cmd"),
            tr("tooltip_restart_desc"),
            tr("tooltip_restart_impact"),
            man_page="systemctl(1)",
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
            man_page="systemctl(1)",
        ))
        self.btn_enable_now.clicked.connect(lambda: self._execute_service_action("enable --now"))
        btn_row.addWidget(self.btn_enable_now)

        self.btn_disable = QPushButton(tr("btn_disable"))
        self.btn_disable.setToolTip(format_tooltip(
            tr("tooltip_disable_title"),
            tr("tooltip_disable_cmd"),
            tr("tooltip_disable_desc"),
            tr("tooltip_disable_impact"),
            man_page="systemctl(1)",
        ))
        self.btn_disable.clicked.connect(lambda: self._execute_service_action("disable"))
        btn_row.addWidget(self.btn_disable)

        svc_control_layout.addLayout(btn_row)
        svc_splitter.addWidget(svc_control)
        svc_layout.addWidget(svc_splitter)
        self.tabs.addTab(svc_tab, tr("tab_services"))

        # ==================== Tab 2: Timers & Scheduler ====================
        timer_tab = QWidget()
        timer_layout = QVBoxLayout(timer_tab)
        timer_layout.setContentsMargins(6, 6, 6, 6)
        timer_layout.setSpacing(8)

        # Filter bar for timers
        timer_filter_bar = QHBoxLayout()
        timer_filter_bar.addWidget(QLabel(tr("lbl_filter_timers")))
        self.txt_filter_timers = QLineEdit()
        self.txt_filter_timers.setPlaceholderText(tr("placeholder_filter_timers"))
        self.txt_filter_timers.textChanged.connect(self._filter_timers)
        timer_filter_bar.addWidget(self.txt_filter_timers)

        btn_new_timer = QPushButton(tr("btn_new_timer_mode"))
        btn_new_timer.setToolTip(tr("tooltip_new_timer_mode"))
        btn_new_timer.clicked.connect(self._enter_new_timer_mode)
        timer_filter_bar.addWidget(btn_new_timer)
        timer_layout.addLayout(timer_filter_bar)

        timer_splitter = QSplitter(Qt.Orientation.Vertical)

        self.tbl_timers = QTableWidget(0, 6)
        self.tbl_timers.setHorizontalHeaderLabels([
            tr("col_timer_next"),
            tr("col_timer_left"),
            tr("col_timer_last"),
            tr("col_timer_unit"),
            tr("col_timer_activates"),
            tr("col_timer_schedule"),
        ])
        self.tbl_timers.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tbl_timers.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.tbl_timers.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.tbl_timers.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.tbl_timers.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self.tbl_timers.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.tbl_timers.setColumnWidth(0, 210)
        self.tbl_timers.setColumnWidth(1, 95)
        self.tbl_timers.setColumnWidth(2, 130)
        self.tbl_timers.setColumnWidth(3, 210)
        self.tbl_timers.setColumnWidth(4, 210)
        self.tbl_timers.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_timers.itemSelectionChanged.connect(self._on_timer_selected)
        timer_splitter.addWidget(self.tbl_timers)

        # Bottom Scrollable Timer Inspector & Schedule Override Editor
        timer_scroll = QScrollArea()
        timer_scroll.setWidgetResizable(True)
        timer_scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        timer_editor_container = QWidget()
        timer_editor_layout = QVBoxLayout(timer_editor_container)
        timer_editor_layout.setContentsMargins(2, 4, 2, 4)
        timer_editor_layout.setSpacing(6)

        self.lbl_timer_summary = QLabel(tr("lbl_select_timer"))
        self.lbl_timer_summary.setStyleSheet("font-size: 13px; font-weight: 600; color: #6899e6; padding: 2px;")
        timer_editor_layout.addWidget(self.lbl_timer_summary)

        gen_box = QGroupBox(tr("group_edit_timer"))
        gen_vbox = QVBoxLayout(gen_box)
        gen_vbox.setSpacing(8)

        lbl_intro = QLabel(tr("lbl_timer_intro"))
        lbl_intro.setWordWrap(True)
        lbl_intro.setStyleSheet("color: #a4a8b3; font-size: 12.5px; line-height: 1.4;")
        gen_vbox.addWidget(lbl_intro)

        gen_grid = QGridLayout()
        gen_grid.setSpacing(6)
        gen_grid.setColumnStretch(1, 1)
        gen_grid.setColumnStretch(3, 1)

        def _hint_label(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #969ba6; font-size: 11.5px; padding-bottom: 4px;")
            return lbl

        # Row 0: Timer Unit Name & Activates Service (Unit=)
        gen_grid.addWidget(QLabel(tr("lbl_timer_name")), 0, 0)
        self.txt_timer_name = QLineEdit("backup-task.timer")
        self.txt_timer_name.setToolTip(format_tooltip(
            tr("tooltip_timer_name_title"),
            tr("tooltip_timer_name_syntax"),
            tr("tooltip_timer_name_desc"),
            can_be_blank=False,
            blank_behavior="Every timer must have a valid unit filename ending in .timer.",
            man_page="systemd.timer(5)",
        ))
        self.txt_timer_name.textChanged.connect(self._update_timer_preview)
        gen_grid.addWidget(self.txt_timer_name, 0, 1)

        gen_grid.addWidget(QLabel(tr("lbl_activates_unit")), 0, 2)
        self.txt_activates_unit = QLineEdit()
        self.txt_activates_unit.setPlaceholderText(tr("placeholder_activates_unit"))
        self.txt_activates_unit.setToolTip(format_tooltip(
            tr("tooltip_activates_title"),
            tr("tooltip_activates_syntax"),
            tr("tooltip_activates_desc"),
            can_be_blank=True,
            blank_behavior="Defaults to activating the .service unit with the same base name as this .timer.",
            default_value="<timer_name>.service",
            man_page="systemd.timer(5)",
        ))
        self.txt_activates_unit.textChanged.connect(self._update_timer_preview)
        gen_grid.addWidget(self.txt_activates_unit, 0, 3)

        # Row 1-2: OnCalendar (with systemd-analyze validator) & OnBootSec
        gen_grid.addWidget(QLabel(tr("lbl_schedule")), 1, 0)
        cal_row = QHBoxLayout()
        cal_row.setSpacing(6)
        self.cmb_schedule = QComboBox()
        self.cmb_schedule.setEditable(True)
        self.cmb_schedule.addItems([
            "",
            "daily",
            "weekly",
            "hourly",
            "monthly",
            "*-*-* 03:00:00",
            "Mon..Fri *-*-* 09:00:00",
            "Mon..Fri 22:30",
            "Sat *-*-1..7 18:00:00",
            "*-*-01 02:00:00",
            "*-*-* *:00/15:00",
        ])
        self.cmb_schedule.setToolTip(format_tooltip(
            tr("tooltip_schedule_title"),
            tr("tooltip_schedule_syntax"),
            tr("tooltip_schedule_desc"),
            can_be_blank=True,
            blank_behavior="No wall-clock calendar trigger is set (use monotonic timers like OnBootSec= or OnUnitActiveSec= instead).",
            example=tr("tooltip_schedule_example"),
            man_page="systemd.time(7)",
        ))
        self.cmb_schedule.currentTextChanged.connect(self._update_timer_preview)
        cal_row.addWidget(self.cmb_schedule, 1)

        self.btn_test_calendar = QPushButton(tr("btn_test_calendar"))
        self.btn_test_calendar.setToolTip(tr("tooltip_test_calendar"))
        self.btn_test_calendar.clicked.connect(self._validate_calendar_schedule)
        cal_row.addWidget(self.btn_test_calendar)
        gen_grid.addLayout(cal_row, 1, 1)

        gen_grid.addWidget(QLabel(tr("lbl_onbootsec")), 1, 2)
        self.cmb_onbootsec = QComboBox()
        self.cmb_onbootsec.setEditable(True)
        self.cmb_onbootsec.addItems(["", "5min", "15min", "30min", "1h"])
        self.cmb_onbootsec.setToolTip(format_tooltip(
            tr("tooltip_onbootsec_title"),
            tr("tooltip_onbootsec_syntax"),
            tr("tooltip_onbootsec_desc"),
            can_be_blank=True,
            blank_behavior="Does not trigger automatically after system boot unless another trigger (e.g. OnCalendar=) is configured.",
            example=tr("tooltip_onbootsec_example"),
            man_page="systemd.timer(5)",
        ))
        self.cmb_onbootsec.currentTextChanged.connect(self._update_timer_preview)
        gen_grid.addWidget(self.cmb_onbootsec, 1, 3)

        gen_grid.addWidget(_hint_label(tr("hint_oncalendar")), 2, 1)
        gen_grid.addWidget(_hint_label(tr("hint_onbootsec")), 2, 3)

        # Row 3-4: OnUnitActiveSec & OnUnitInactiveSec
        gen_grid.addWidget(QLabel(tr("lbl_onunitactivesec")), 3, 0)
        self.cmb_onunitactivesec = QComboBox()
        self.cmb_onunitactivesec.setEditable(True)
        self.cmb_onunitactivesec.addItems(["", "15min", "1h", "6h", "12h", "1d", "1w"])
        self.cmb_onunitactivesec.setToolTip(format_tooltip(
            tr("tooltip_onunitactivesec_title"),
            tr("tooltip_onunitactivesec_syntax"),
            tr("tooltip_onunitactivesec_desc"),
            can_be_blank=True,
            blank_behavior="No recurring interval relative to when the target service was last activated.",
            example=tr("tooltip_onunitactivesec_example"),
            man_page="systemd.timer(5)",
        ))
        self.cmb_onunitactivesec.currentTextChanged.connect(self._update_timer_preview)
        gen_grid.addWidget(self.cmb_onunitactivesec, 3, 1)

        gen_grid.addWidget(QLabel(tr("lbl_onunitinactivesec")), 3, 2)
        self.cmb_onunitinactivesec = QComboBox()
        self.cmb_onunitinactivesec.setEditable(True)
        self.cmb_onunitinactivesec.addItems(["", "15min", "30min", "1h", "6h", "1d"])
        self.cmb_onunitinactivesec.setToolTip(format_tooltip(
            tr("tooltip_onunitinactivesec_title"),
            tr("tooltip_onunitinactivesec_syntax"),
            tr("tooltip_onunitinactivesec_desc"),
            can_be_blank=True,
            blank_behavior="No recurring interval relative to when the target service last finished/deactivated.",
            example=tr("tooltip_onunitinactivesec_example"),
            man_page="systemd.timer(5)",
        ))
        self.cmb_onunitinactivesec.currentTextChanged.connect(self._update_timer_preview)
        gen_grid.addWidget(self.cmb_onunitinactivesec, 3, 3)

        gen_grid.addWidget(_hint_label(tr("hint_onunitactivesec")), 4, 1)
        gen_grid.addWidget(_hint_label(tr("hint_onunitinactivesec")), 4, 3)

        # Row 5-6: OnStartupSec & OnActiveSec
        gen_grid.addWidget(QLabel(tr("lbl_onstartupsec")), 5, 0)
        self.cmb_onstartupsec = QComboBox()
        self.cmb_onstartupsec.setEditable(True)
        self.cmb_onstartupsec.addItems(["", "1min", "5min", "15min", "30min"])
        self.cmb_onstartupsec.setToolTip(format_tooltip(
            tr("tooltip_onstartupsec_title"),
            tr("tooltip_onstartupsec_syntax"),
            tr("tooltip_onstartupsec_desc"),
            can_be_blank=True,
            blank_behavior="Does not trigger relative to service manager startup.",
            example=tr("tooltip_onstartupsec_example"),
            man_page="systemd.timer(5)",
        ))
        self.cmb_onstartupsec.currentTextChanged.connect(self._update_timer_preview)
        gen_grid.addWidget(self.cmb_onstartupsec, 5, 1)

        gen_grid.addWidget(QLabel(tr("lbl_onactivesec")), 5, 2)
        self.cmb_onactivesec = QComboBox()
        self.cmb_onactivesec.setEditable(True)
        self.cmb_onactivesec.addItems(["", "30s", "1min", "5min", "15min", "1h"])
        self.cmb_onactivesec.setToolTip(format_tooltip(
            tr("tooltip_onactivesec_title"),
            tr("tooltip_onactivesec_syntax"),
            tr("tooltip_onactivesec_desc"),
            can_be_blank=True,
            blank_behavior="Does not trigger relative to when the .timer unit itself was activated.",
            example=tr("tooltip_onactivesec_example"),
            man_page="systemd.timer(5)",
        ))
        self.cmb_onactivesec.currentTextChanged.connect(self._update_timer_preview)
        gen_grid.addWidget(self.cmb_onactivesec, 5, 3)

        gen_grid.addWidget(_hint_label(tr("hint_onstartupsec")), 6, 1)
        gen_grid.addWidget(_hint_label(tr("hint_onactivesec")), 6, 3)

        # Row 7-8: RandomizedDelaySec & AccuracySec
        gen_grid.addWidget(QLabel(tr("lbl_randomizeddelaysec")), 7, 0)
        self.cmb_randomizeddelaysec = QComboBox()
        self.cmb_randomizeddelaysec.setEditable(True)
        self.cmb_randomizeddelaysec.addItems(["", "0", "5min", "15min", "30min", "1h", "100min", "6h"])
        self.cmb_randomizeddelaysec.setToolTip(format_tooltip(
            tr("tooltip_randomizeddelaysec_title"),
            tr("tooltip_randomizeddelaysec_syntax"),
            tr("tooltip_randomizeddelaysec_desc"),
            can_be_blank=True,
            blank_behavior="No random jitter delay is added; timer fires at its exact scheduled time.",
            default_value="0 (no random delay)",
            example=tr("tooltip_randomizeddelaysec_example"),
            man_page="systemd.timer(5)",
        ))
        self.cmb_randomizeddelaysec.currentTextChanged.connect(self._update_timer_preview)
        gen_grid.addWidget(self.cmb_randomizeddelaysec, 7, 1)

        gen_grid.addWidget(QLabel(tr("lbl_accuracysec")), 7, 2)
        self.cmb_accuracysec = QComboBox()
        self.cmb_accuracysec.setEditable(True)
        self.cmb_accuracysec.addItems(["", "1min", "1s", "1us", "15min", "1h", "12h"])
        self.cmb_accuracysec.setToolTip(format_tooltip(
            tr("tooltip_accuracysec_title"),
            tr("tooltip_accuracysec_syntax"),
            tr("tooltip_accuracysec_desc"),
            can_be_blank=True,
            blank_behavior="Uses systemd's default 1min coalescing window to save CPU/battery wakeups.",
            default_value="1min",
            example=tr("tooltip_accuracysec_example"),
            man_page="systemd.timer(5)",
        ))
        self.cmb_accuracysec.currentTextChanged.connect(self._update_timer_preview)
        gen_grid.addWidget(self.cmb_accuracysec, 7, 3)

        gen_grid.addWidget(_hint_label(tr("hint_randomizeddelaysec")), 8, 1)
        gen_grid.addWidget(_hint_label(tr("hint_accuracysec")), 8, 3)

        # Row 9-12: Checkboxes (Persistent, FixedRandomDelay, WakeSystem, OnClockChange/OnTimezoneChange)
        self.chk_persistent = QCheckBox(tr("chk_persistent"))
        self.chk_persistent.setChecked(True)
        self.chk_persistent.setToolTip(format_tooltip(
            tr("tooltip_persistent_title"),
            tr("tooltip_persistent_syntax"),
            tr("tooltip_persistent_desc"),
            default_value="false",
            recommended_value="true for daily/weekly OnCalendar= maintenance tasks on desktops/laptops",
            man_page="systemd.timer(5)",
        ))
        self.chk_persistent.toggled.connect(self._update_timer_preview)
        gen_grid.addWidget(self.chk_persistent, 9, 0, 1, 4)

        self.chk_fixedrandomdelay = QCheckBox(tr("chk_fixedrandomdelay"))
        self.chk_fixedrandomdelay.setToolTip(format_tooltip(
            tr("tooltip_fixedrandomdelay_title"),
            tr("tooltip_fixedrandomdelay_syntax"),
            tr("tooltip_fixedrandomdelay_desc"),
            default_value="false",
            recommended_value="true when RandomizedDelaySec= is used on machines that reboot frequently",
            man_page="systemd.timer(5)",
        ))
        self.chk_fixedrandomdelay.toggled.connect(self._update_timer_preview)
        gen_grid.addWidget(self.chk_fixedrandomdelay, 10, 0, 1, 4)

        self.chk_wakesystem = QCheckBox(tr("chk_wakesystem"))
        self.chk_wakesystem.setToolTip(format_tooltip(
            tr("tooltip_wakesystem_title"),
            tr("tooltip_wakesystem_syntax"),
            tr("tooltip_wakesystem_desc"),
            default_value="false",
            security=tr("tooltip_wakesystem_impact"),
            man_page="systemd.timer(5)",
        ))
        self.chk_wakesystem.toggled.connect(self._update_timer_preview)
        gen_grid.addWidget(self.chk_wakesystem, 11, 0, 1, 4)

        self.chk_onclockchange = QCheckBox(tr("chk_onclockchange"))
        self.chk_onclockchange.setToolTip(format_tooltip(
            tr("tooltip_onclockchange_title"),
            tr("tooltip_onclockchange_syntax"),
            tr("tooltip_onclockchange_desc"),
            default_value="false",
            man_page="systemd.timer(5)",
        ))
        self.chk_onclockchange.toggled.connect(self._update_timer_preview)
        gen_grid.addWidget(self.chk_onclockchange, 12, 0, 1, 2)

        self.chk_ontimezonechange = QCheckBox(tr("chk_ontimezonechange"))
        self.chk_ontimezonechange.setToolTip(format_tooltip(
            tr("tooltip_ontimezonechange_title"),
            tr("tooltip_ontimezonechange_syntax"),
            tr("tooltip_ontimezonechange_desc"),
            default_value="false",
            man_page="systemd.timer(5)",
        ))
        self.chk_ontimezonechange.toggled.connect(self._update_timer_preview)
        gen_grid.addWidget(self.chk_ontimezonechange, 12, 2, 1, 2)

        gen_vbox.addLayout(gen_grid)

        # Timer Action Bar
        timer_btn_row = QHBoxLayout()
        timer_btn_row.setSpacing(6)

        self.btn_run_target = QPushButton(tr("btn_run_target_now"))
        self.btn_run_target.setToolTip(tr("tooltip_run_target_now"))
        self.btn_run_target.clicked.connect(self._trigger_timer_target_now)
        timer_btn_row.addWidget(self.btn_run_target)

        self.btn_enable_timer = QPushButton(tr("btn_enable_timer"))
        self.btn_enable_timer.clicked.connect(lambda: self._execute_timer_action("enable --now"))
        timer_btn_row.addWidget(self.btn_enable_timer)

        self.btn_disable_timer = QPushButton(tr("btn_disable_timer"))
        self.btn_disable_timer.clicked.connect(lambda: self._execute_timer_action("disable"))
        timer_btn_row.addWidget(self.btn_disable_timer)

        self.btn_revert_override = QPushButton(tr("btn_revert_override"))
        self.btn_revert_override.setToolTip(tr("tooltip_revert_override"))
        self.btn_revert_override.setEnabled(False)
        self.btn_revert_override.clicked.connect(self._revert_timer_override)
        timer_btn_row.addWidget(self.btn_revert_override)

        timer_btn_row.addStretch()

        self.btn_save_timer = QPushButton(tr("btn_save_timer"))
        self.btn_save_timer.setObjectName("primaryBtn")
        self.btn_save_timer.setToolTip(tr("tooltip_save_timer"))
        self.btn_save_timer.clicked.connect(self._save_timer_changes)
        timer_btn_row.addWidget(self.btn_save_timer)

        gen_vbox.addLayout(timer_btn_row)
        timer_editor_layout.addWidget(gen_box)

        timer_scroll.setWidget(timer_editor_container)
        timer_splitter.addWidget(timer_scroll)
        timer_splitter.setSizes([240, 420])
        timer_layout.addWidget(timer_splitter)
        self.tabs.addTab(timer_tab, tr("tab_timers"))

        layout.addWidget(self.tabs)

    def _on_scope_changed(self) -> None:
        self.user_mode = self.rb_user.isChecked()
        self.refresh_all()

    def refresh_all(self) -> None:
        def _fetch():
            services = SystemdManager.list_services(self.user_mode)
            timers = SystemdManager.list_timers(self.user_mode)
            return services, timers

        services, timers = run_with_loading_modal(
            self,
            title="Loading Systemd Units...",
            subtitle="Querying service states and timer schedules...",
            task_fn=_fetch,
        )
        self._populate_services(services)
        self._populate_timers(timers)

    def _load_services(self) -> None:
        services = run_with_loading_modal(
            self,
            title="Loading Systemd Services...",
            subtitle="Querying systemctl service units...",
            task_fn=lambda: SystemdManager.list_services(self.user_mode),
        )
        self._populate_services(services)

    def _populate_services(self, services: list[ServiceUnit]) -> None:
        self.tbl_services.setRowCount(0)
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
        timers = run_with_loading_modal(
            self,
            title="Loading Systemd Timers...",
            subtitle="Querying systemctl timer schedules...",
            task_fn=lambda: SystemdManager.list_timers(self.user_mode),
        )
        self._populate_timers(timers)

    def _populate_timers(self, timers: list[TimerUnit]) -> None:
        self.tbl_timers.setRowCount(0)
        row = 0
        for t in timers:
            self.tbl_timers.insertRow(row)
            self.tbl_timers.setItem(row, 0, QTableWidgetItem(t.next_elapse))
            self.tbl_timers.setItem(row, 1, QTableWidgetItem(t.left))
            last_str = t.passed if t.passed and t.passed != "-" else t.last_trigger
            self.tbl_timers.setItem(row, 2, QTableWidgetItem(last_str))
            self.tbl_timers.setItem(row, 3, QTableWidgetItem(t.unit))
            self.tbl_timers.setItem(row, 4, QTableWidgetItem(t.activates))
            self.tbl_timers.setItem(row, 5, QTableWidgetItem(t.schedule_summary))
            self.tbl_timers.item(row, 0).setData(Qt.ItemDataRole.UserRole, t)
            row += 1

        if self.tbl_timers.rowCount() > 0 and not self.selected_timer:
            self.tbl_timers.selectRow(0)

    def _filter_services(self, text: str) -> None:
        needle = text.lower()
        for row in range(self.tbl_services.rowCount()):
            item = self.tbl_services.item(row, 0)
            desc = self.tbl_services.item(row, 3)
            matches = (item and needle in item.text().lower()) or (desc and needle in desc.text().lower())
            self.tbl_services.setRowHidden(row, not matches)

    def _filter_timers(self, text: str) -> None:
        needle = text.lower()
        for row in range(self.tbl_timers.rowCount()):
            u_item = self.tbl_timers.item(row, 3)
            a_item = self.tbl_timers.item(row, 4)
            s_item = self.tbl_timers.item(row, 5)
            matches = (
                (u_item and needle in u_item.text().lower())
                or (a_item and needle in a_item.text().lower())
                or (s_item and needle in s_item.text().lower())
            )
            self.tbl_timers.setRowHidden(row, not matches)

    def _on_service_selected(self) -> None:
        selected = self.tbl_services.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        svc: ServiceUnit = self.tbl_services.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.selected_service = svc.name

        self.lbl_svc_summary.setText(
            tr(
                "lbl_svc_summary",
                name=svc.name,
                status=svc.friendly_status,
                boot=svc.friendly_boot,
            )
        )

        cmd_preview = SystemdManager.build_command_str("status", svc.name, self.user_mode)
        self.preview_banner.set_text(cmd_preview)

        status_output = SystemdManager.get_unit_status(svc.name, self.user_mode)
        self.txt_status.setPlainText(status_output)

    def _on_timer_selected(self) -> None:
        selected = self.tbl_timers.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        timer: TimerUnit = self.tbl_timers.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.selected_timer = timer.unit
        self.creating_new_timer = False

        cfg = SystemdManager.get_timer_config(timer.unit, user_mode=self.user_mode, activates=timer.activates)
        self.active_timer_config = cfg
        self._populate_timer_form(cfg)

    def _populate_timer_form(self, cfg: TimerConfig) -> None:
        self._is_updating_timer_ui = True
        self.txt_timer_name.setText(cfg.unit_name)
        self.txt_timer_name.setReadOnly(not self.creating_new_timer)
        self.txt_activates_unit.setText(cfg.activates)
        self.cmb_schedule.setCurrentText(cfg.on_calendar)
        self.cmb_onbootsec.setCurrentText(cfg.on_boot_sec)
        self.cmb_onstartupsec.setCurrentText(cfg.on_startup_sec)
        self.cmb_onactivesec.setCurrentText(cfg.on_active_sec)
        self.cmb_onunitactivesec.setCurrentText(cfg.on_unit_active_sec)
        self.cmb_onunitinactivesec.setCurrentText(cfg.on_unit_inactive_sec)
        self.cmb_randomizeddelaysec.setCurrentText(cfg.randomized_delay_sec)
        self.cmb_accuracysec.setCurrentText(cfg.accuracy_sec)
        self.chk_persistent.setChecked(cfg.persistent)
        self.chk_fixedrandomdelay.setChecked(cfg.fixed_random_delay)
        self.chk_wakesystem.setChecked(cfg.wake_system)
        self.chk_onclockchange.setChecked(cfg.on_clock_change)
        self.chk_ontimezonechange.setChecked(cfg.on_timezone_change)
        self._is_updating_timer_ui = False

        override_path = SystemdManager.get_timer_override_path(cfg.unit_name, self.user_mode)
        has_override = bool(cfg.dropin_paths) or os.path.exists(override_path)
        self.btn_revert_override.setEnabled(has_override and not self.creating_new_timer)
        self.btn_save_timer.setText(
            tr("btn_save_new_timer") if self.creating_new_timer else tr("btn_save_timer")
        )

        if self.creating_new_timer:
            target_p = SystemdManager.get_new_timer_unit_path(cfg.unit_name, self.user_mode)
            self.lbl_timer_summary.setText(tr("lbl_timer_new_summary", unit=cfg.unit_name, source=target_p))
        else:
            src = cfg.fragment_path or "(system unit)"
            if cfg.dropin_paths:
                src += f" + override ({', '.join(cfg.dropin_paths)})"
            self.lbl_timer_summary.setText(
                tr("lbl_timer_selected_summary", unit=cfg.unit_name, activates=cfg.activates, source=src)
            )

        self._update_timer_preview()

    def _enter_new_timer_mode(self) -> None:
        self.tbl_timers.clearSelection()
        self.creating_new_timer = True
        self.selected_timer = ""
        new_cfg = TimerConfig(
            unit_name="backup-task.timer",
            activates="backup-task.service",
            description="Custom scheduled task timer",
            on_calendar="daily",
            persistent=True,
        )
        self.active_timer_config = new_cfg
        self._populate_timer_form(new_cfg)
        self.txt_timer_name.setFocus()

    def _build_current_timer_config(self) -> TimerConfig:
        name = self.txt_timer_name.text().strip() or "custom-task.timer"
        if not name.endswith(".timer"):
            name += ".timer"
        activates = self.txt_activates_unit.text().strip() or re.sub(r"\.timer$", ".service", name)
        return TimerConfig(
            unit_name=name,
            activates=activates,
            description=self.active_timer_config.description,
            fragment_path=self.active_timer_config.fragment_path,
            dropin_paths=list(self.active_timer_config.dropin_paths),
            on_calendar=self.cmb_schedule.currentText().strip(),
            on_boot_sec=self.cmb_onbootsec.currentText().strip(),
            on_startup_sec=self.cmb_onstartupsec.currentText().strip(),
            on_active_sec=self.cmb_onactivesec.currentText().strip(),
            on_unit_active_sec=self.cmb_onunitactivesec.currentText().strip(),
            on_unit_inactive_sec=self.cmb_onunitinactivesec.currentText().strip(),
            randomized_delay_sec=self.cmb_randomizeddelaysec.currentText().strip(),
            accuracy_sec=self.cmb_accuracysec.currentText().strip(),
            persistent=self.chk_persistent.isChecked(),
            fixed_random_delay=self.chk_fixedrandomdelay.isChecked(),
            wake_system=self.chk_wakesystem.isChecked(),
            on_clock_change=self.chk_onclockchange.isChecked(),
            on_timezone_change=self.chk_ontimezonechange.isChecked(),
        )

    def _validate_calendar_schedule(self) -> None:
        expr = self.cmb_schedule.currentText().strip()
        ok, output = SystemdManager.validate_calendar_expression(expr)
        if ok:
            QMessageBox.information(self, tr("title_calendar_valid"), output)
        else:
            QMessageBox.warning(self, tr("title_calendar_invalid"), output)

    def _update_timer_preview(self) -> None:
        if self._is_updating_timer_ui:
            return
        cfg = self._build_current_timer_config()
        if self.creating_new_timer:
            preview_text = cfg.to_unit_file_content()
        else:
            preview_text = cfg.to_override_content()
        self.preview_banner.set_text(preview_text)

    def _save_timer_changes(self) -> None:
        cfg = self._build_current_timer_config()
        if not any([
            cfg.on_calendar,
            cfg.on_boot_sec,
            cfg.on_startup_sec,
            cfg.on_active_sec,
            cfg.on_unit_active_sec,
            cfg.on_unit_inactive_sec,
            cfg.on_clock_change,
            cfg.on_timezone_change,
        ]):
            QMessageBox.warning(self, tr("title_missing_trigger"), tr("msg_missing_trigger"))
            return

        if self.creating_new_timer:
            target_path = SystemdManager.get_new_timer_unit_path(cfg.unit_name, self.user_mode)
            content = cfg.to_unit_file_content()
            notes = [
                tr("note_timer_target_path", path=target_path),
                tr("note_timer_daemon_reload"),
            ]
        else:
            target_path = SystemdManager.get_timer_override_path(cfg.unit_name, self.user_mode)
            content = cfg.to_override_content()
            notes = [
                tr("note_timer_target_path", path=target_path),
                tr("note_timer_reset_explained"),
                tr("note_timer_daemon_reload"),
            ]
        if not self.user_mode:
            notes.append(tr("note_elevates_scope"))

        self.preview_banner.set_text(content)
        dlg = SafetyExecutionDialog(
            title=tr("dialog_save_timer_title"),
            target_path_or_command=target_path,
            diff_text=content,
            safety_notes=notes,
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = SystemdManager.save_timer_config(
                cfg,
                user_mode=self.user_mode,
                create_new_unit=self.creating_new_timer,
            )
            if res.success:
                QMessageBox.information(self, tr("title_success"), tr("msg_timer_saved", path=target_path))
                self.selected_timer = cfg.unit_name
                self.creating_new_timer = False
                self._load_timers()
            else:
                QMessageBox.critical(
                    self,
                    tr("title_action_failed"),
                    tr("msg_action_failed", error=res.stderr or res.stdout),
                )

    def _revert_timer_override(self) -> None:
        unit = self.txt_timer_name.text().strip()
        if not unit:
            return
        override_path = SystemdManager.get_timer_override_path(unit, self.user_mode)
        dlg = SafetyExecutionDialog(
            title=tr("dialog_revert_timer_title", unit=unit),
            target_path_or_command=override_path,
            safety_notes=[
                tr("note_revert_timer", path=override_path),
                tr("note_timer_daemon_reload"),
            ],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = SystemdManager.revert_timer_override(unit, user_mode=self.user_mode)
            if res.success:
                QMessageBox.information(self, tr("title_success"), tr("msg_timer_reverted", unit=unit))
                self._load_timers()
                self._on_timer_selected()
            else:
                QMessageBox.critical(
                    self,
                    tr("title_action_failed"),
                    tr("msg_action_failed", error=res.stderr or res.stdout),
                )

    def _trigger_timer_target_now(self) -> None:
        cfg = self._build_current_timer_config()
        target_svc = cfg.activates
        if not target_svc:
            QMessageBox.warning(self, tr("title_no_timer_selected"), tr("msg_select_timer_first"))
            return
        self._run_unit_action_with_dialog("start", target_svc)

    def _execute_timer_action(self, action: str) -> None:
        unit = self.txt_timer_name.text().strip()
        if not unit:
            QMessageBox.warning(self, tr("title_no_timer_selected"), tr("msg_select_timer_first"))
            return
        self._run_unit_action_with_dialog(action, unit)

    def _execute_service_action(self, action: str) -> None:
        if not self.selected_service:
            QMessageBox.warning(self, tr("title_no_service_selected"), tr("msg_select_service_first"))
            return
        self._run_unit_action_with_dialog(action, self.selected_service)

    def _run_unit_action_with_dialog(self, action: str, unit_name: str) -> None:
        cmd_str = SystemdManager.build_command_str(action, unit_name, self.user_mode)
        self.preview_banner.set_text(cmd_str)

        dlg = SafetyExecutionDialog(
            title=tr("dialog_exec_title", action=action),
            target_path_or_command=cmd_str,
            safety_notes=[
                tr("note_modifies_service", service=unit_name),
                tr("note_elevates_scope"),
            ],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = SystemdManager.execute_unit_action(action, unit_name, self.user_mode)
            if res.success:
                QMessageBox.information(self, tr("title_success"), tr("msg_exec_success", command=cmd_str))
                self.refresh_all()
                if unit_name.endswith(".service"):
                    self._on_service_selected()
            else:
                QMessageBox.critical(
                    self,
                    tr("title_action_failed"),
                    tr("msg_action_failed", error=res.stderr or res.stdout),
                )

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
