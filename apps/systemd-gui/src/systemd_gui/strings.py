"""User-facing strings for the systemd-gui application.

See :mod:`linux_gui_core.i18n` for how localisation works.
"""

from linux_gui_core.i18n import StringTable

EN: dict[str, str] = {
    # Main window
    "window_title": "systemd Service & Timer Explorer",
    "preview_title": "Systemctl Command Preview",
    "preview_subtitle": "Shows the exact systemctl command and flags before execution. Hover over actions for safety tooltips.",

    # Scope bar
    "lbl_target_scope": "Target Scope:",
    "rb_system": "System Scope (/etc/systemd/system, requires root)",
    "rb_user": "User Session (~/.config/systemd/user, rootless)",
    "btn_daemon_reload": "daemon-reload",
    "tooltip_daemon_reload_title": "Reload systemd manager",
    "tooltip_daemon_reload_cmd": "systemctl daemon-reload",
    "tooltip_daemon_reload_desc": "Rereads all generator and unit files. Run this after modifying any .service or .timer file.",
    "tooltip_daemon_reload_safety": "Safe / Required after edits",
    "btn_refresh": "Refresh List",

    # Services Tab
    "tab_services": "Services",
    "lbl_filter_services": "Filter Services:",
    "placeholder_filter_services": "Search service name or description (e.g. bluetooth, ssh, docker)...",
    "col_svc_name": "Service Unit Name",
    "col_svc_state": "Current Running State",
    "col_svc_boot": "Starts on Boot?",
    "col_svc_desc": "Description",
    "lbl_select_svc": "Select a service above to inspect status and run actions.",
    "lbl_svc_summary": "Service: <b>{name}</b> &nbsp;|&nbsp; State: <b>{status}</b> &nbsp;|&nbsp; Boot Startup: <b>{boot}</b>",

    # Action buttons
    "btn_start": "Start Service",
    "tooltip_start_title": "Start Service",
    "tooltip_start_cmd": "systemctl start <unit>",
    "tooltip_start_desc": "Starts (activates) the service immediately.",
    "tooltip_start_impact": "Standard operation",

    "btn_stop": "Stop Service",
    "tooltip_stop_title": "Stop Service",
    "tooltip_stop_cmd": "systemctl stop <unit>",
    "tooltip_stop_desc": "Stops (deactivates) the running service immediately.",
    "tooltip_stop_impact": "Standard operation",

    "btn_restart": "Restart Service",
    "tooltip_restart_title": "Restart Service",
    "tooltip_restart_cmd": "systemctl restart <unit>",
    "tooltip_restart_desc": "Stops and immediately restarts the service. Useful after configuration changes.",
    "tooltip_restart_impact": "Standard operation",

    "btn_enable_now": "Enable to Run on Boot",
    "tooltip_enable_now_title": "Enable with --now",
    "tooltip_enable_now_cmd": "systemctl enable --now <unit>",
    "tooltip_enable_now_desc": "Configures systemd to start this service every time your computer boots AND starts it right away.",
    "tooltip_enable_now_impact": "Safe / Recommended",

    "btn_disable": "Disable Boot Startup",
    "tooltip_disable_title": "Disable Service",
    "tooltip_disable_cmd": "systemctl disable <unit>",
    "tooltip_disable_desc": "Removes automatic startup on boot. Does not terminate the currently running process.",
    "tooltip_disable_impact": "Safe",

    # Timers Tab
    "tab_timers": "Timers & Scheduler",
    "col_timer_next": "Next Scheduled Trigger",
    "col_timer_left": "Trigger In",
    "col_timer_unit": "Timer Unit",
    "col_timer_activates": "Activates Service",

    "group_create_timer": "Create New Scheduled Timer (systemd Timer Builder)",
    "lbl_timer_name": "Timer Unit Name:",
    "lbl_schedule": "Schedule (OnCalendar):",
    "tooltip_schedule_title": "OnCalendar Format",
    "tooltip_schedule_syntax": "OnCalendar=daily",
    "tooltip_schedule_desc": "Defines the calendar expression when the timer activates the associated service.",
    "tooltip_schedule_impact": "Safe",
    "tooltip_schedule_example": "*-*-* 04:30:00 (every day at 4:30 AM)",

    "chk_persistent": "Persistent=true (Run missed events immediately if computer was off/asleep)",
    "tooltip_persistent_title": "Persistent Trigger",
    "tooltip_persistent_syntax": "Persistent=true",
    "tooltip_persistent_desc": "Ensures missed timers (due to suspended or turned-off PC) trigger as soon as the machine boots up.",
    "tooltip_persistent_impact": "Recommended for backups",

    # Dialogs & notifications
    "title_no_service_selected": "No Service Selected",
    "msg_select_service_first": "Please select a service from the list first.",
    "dialog_exec_title": "Execute: {action}",
    "note_modifies_service": "Modifies state of {service}",
    "note_elevates_scope": "Elevates with pkexec/sudo if system scope",
    "title_success": "Success",
    "msg_exec_success": "Executed:\n{command}",
    "title_action_failed": "Action Failed",
    "msg_action_failed": "Error:\n{error}",
    "dialog_daemon_reload_title": "systemd daemon-reload",
    "note_reload_configs": "Reloads all systemd configurations into memory.",
    "title_reloaded": "Reloaded",
    "msg_daemon_reload_success": "daemon-reload completed successfully.",
    "title_error": "Error",
    "msg_daemon_reload_failed": "Failed:\n{error}",
}

STRINGS: dict[str, dict[str, str]] = {
    "en": EN,
}

tr = StringTable(STRINGS)
