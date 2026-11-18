"""User-facing strings for the systemd-gui application.

See :mod:`linux_gui_core.i18n` for how localisation works.
"""

from linux_gui_core.i18n import StringTable

EN: dict[str, str] = {
    # Main window
    "window_title": "systemd Service & Timer Explorer",
    "preview_title": "systemctl & Unit Override Preview",
    "preview_subtitle": "Shows the exact systemctl command or systemd.timer(5) drop-in override before execution.",

    # Scope bar
    "lbl_target_scope": "Target Scope:",
    "rb_system": "System Scope (/etc/systemd/system, requires root)",
    "rb_user": "User Session (~/.config/systemd/user, rootless)",
    "btn_daemon_reload": "daemon-reload",
    "tooltip_daemon_reload_title": "Reload systemd Manager Configuration",
    "tooltip_daemon_reload_cmd": "systemctl daemon-reload",
    "tooltip_daemon_reload_desc": (
        "Reloads the systemd manager configuration. Reruns all generators (systemd.generator(7)), "
        "reloads all unit files and drop-in overrides from disk, and recreates the entire dependency tree."
    ),
    "tooltip_daemon_reload_safety": "Safe / Required after unit edits",
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

    # Service Action buttons
    "btn_start": "Start Service",
    "tooltip_start_title": "Start (Activate) Unit",
    "tooltip_start_cmd": "systemctl start <unit>",
    "tooltip_start_desc": "Starts (activates) the specified service unit immediately during the current session.",
    "tooltip_start_impact": "Standard operation",

    "btn_stop": "Stop Service",
    "tooltip_stop_title": "Stop (Deactivate) Unit",
    "tooltip_stop_cmd": "systemctl stop <unit>",
    "tooltip_stop_desc": "Stops (deactivates) the specified running service unit immediately.",
    "tooltip_stop_impact": "Standard operation",

    "btn_restart": "Restart Service",
    "tooltip_restart_title": "Restart Unit",
    "tooltip_restart_cmd": "systemctl restart <unit>",
    "tooltip_restart_desc": "Stops and then starts the unit. If the unit is not running yet, it will be started.",
    "tooltip_restart_impact": "Standard operation",

    "btn_enable_now": "Enable to Run on Boot",
    "tooltip_enable_now_title": "Enable & Start Unit (--now)",
    "tooltip_enable_now_cmd": "systemctl enable --now <unit>",
    "tooltip_enable_now_desc": (
        "Enables the unit by creating symlinks as configured in its [Install] section so it starts on boot, "
        "and simultaneously starts the unit immediately (--now)."
    ),
    "tooltip_enable_now_impact": "Safe / Recommended",

    "btn_disable": "Disable Boot Startup",
    "tooltip_disable_title": "Disable Unit",
    "tooltip_disable_cmd": "systemctl disable <unit>",
    "tooltip_disable_desc": (
        "Disables the unit by removing the symlinks to it from the unit configuration directories. "
        "Does not implicitly stop the unit if it is currently running."
    ),
    "tooltip_disable_impact": "Safe",

    # Timers Tab
    "tab_timers": "Timers & Scheduler",
    "lbl_filter_timers": "Filter Timers:",
    "placeholder_filter_timers": "Search timer unit, target service, or schedule (e.g. fstrim, daily, tmpfiles)...",
    "col_timer_next": "Next Scheduled Trigger",
    "col_timer_left": "Trigger In",
    "col_timer_last": "Last Triggered",
    "col_timer_unit": "Timer Unit",
    "col_timer_activates": "Activates Unit",
    "col_timer_schedule": "Configured Schedule",

    "lbl_timer_selected_summary": (
        "Selected Timer: <b>{unit}</b> &nbsp;|&nbsp; Activates: <code>{activates}</code> "
        "&nbsp;|&nbsp; Source: <code>{source}</code>"
    ),
    "lbl_timer_new_summary": "Creating New Timer Unit: <b>{unit}</b> &nbsp;|&nbsp; Target Path: <code>{source}</code>",
    "lbl_select_timer": "Select an existing timer above to inspect and adjust its schedule, or click 'New Timer Unit'.",

    # Timer Editor Groups & Explanations
    "group_edit_timer": "Adjust Timer Schedule & Behavior (systemd.timer(5) Inspector & Override Editor)",
    "lbl_timer_intro": (
        "Select any timer above to load its live configuration. systemd supports two types of timer triggers "
        "(which can be used individually or combined): <b>Realtime (Wall-Clock) Timers</b> via <code>OnCalendar=</code> "
        "and <b>Monotonic (Relative Interval) Timers</b> via <code>OnBootSec=</code>, <code>OnUnitActiveSec=</code>, etc. "
        "Saving an existing timer writes a clean drop-in override in <code>.timer.d/override.conf</code>."
    ),

    "lbl_timer_name": "Timer Unit Name:",
    "tooltip_timer_name_title": "Timer Unit Filename",
    "tooltip_timer_name_syntax": "<name>.timer",
    "tooltip_timer_name_desc": (
        "A unit configuration file whose name ends in '.timer' encodes information about a timer controlled "
        "and supervised by systemd. By default, a service by the same name (e.g. foo.service for foo.timer) "
        "is activated when the timer elapses."
    ),

    "lbl_activates_unit": "Activates Service (Unit=):",
    "placeholder_activates_unit": "e.g. backup-task.service (defaults to matching .service name)",
    "tooltip_activates_title": "Target Unit to Activate",
    "tooltip_activates_syntax": "Unit=<name>.service",
    "tooltip_activates_desc": (
        "The unit to activate when this timer elapses. If omitted, defaults to a .service unit with the "
        "same base name as the .timer unit (per systemd.timer(5), it is recommended that both share the same base name)."
    ),

    # Realtime / Calendar Section
    "lbl_schedule": "OnCalendar= (Wall-Clock):",
    "hint_oncalendar": "Realtime calendar expression (e.g. 'daily', 'weekly', '*-*-* 03:00:00'). Leave blank if using monotonic intervals only.",
    "tooltip_schedule_title": "Realtime Wall-Clock Timer (OnCalendar=)",
    "tooltip_schedule_syntax": "OnCalendar=daily | weekly | *-*-* 04:00:00",
    "tooltip_schedule_desc": (
        "Defines realtime (wallclock) timers with calendar event expressions (see systemd.time(7)). "
        "Triggers at specific dates or times of day. Timer units with OnCalendar= are automatically ordered "
        "after time-sync.target."
    ),
    "tooltip_schedule_impact": "Safe",
    "tooltip_schedule_example": "daily, weekly, Mon..Fri *-*-* 09:00:00, *-*-* 04:30:00",

    # Monotonic Timers Section
    "lbl_onbootsec": "OnBootSec= (After Boot):",
    "hint_onbootsec": "Time after machine boot-up before first run (e.g. '15min', '5min').",
    "tooltip_onbootsec_title": "Monotonic Delay After Boot (OnBootSec=)",
    "tooltip_onbootsec_syntax": "OnBootSec=15min",
    "tooltip_onbootsec_desc": (
        "Defines a monotonic timer relative to when the machine was booted up. Commonly paired with "
        "OnUnitActiveSec= so a service runs shortly after boot and repeats at regular intervals thereafter."
    ),
    "tooltip_onbootsec_example": "15min, 2min 30s, 1h",

    "lbl_onstartupsec": "OnStartupSec= (Manager Start):",
    "hint_onstartupsec": "Time after systemd service manager started (ideal for --user timers on first login).",
    "tooltip_onstartupsec_title": "Monotonic Delay After Manager Start (OnStartupSec=)",
    "tooltip_onstartupsec_syntax": "OnStartupSec=5min",
    "tooltip_onstartupsec_desc": (
        "Defines a monotonic timer relative to when the service manager was first started. Particularly useful "
        "for per-user (--user) timer units, where the user service manager starts on first login rather than at system boot."
    ),
    "tooltip_onstartupsec_example": "5min, 30s",

    "lbl_onactivesec": "OnActiveSec= (After Timer Start):",
    "hint_onactivesec": "Time after the .timer unit itself was last activated (e.g. '30s', '5min').",
    "tooltip_onactivesec_title": "Monotonic Delay After Timer Activation (OnActiveSec=)",
    "tooltip_onactivesec_syntax": "OnActiveSec=30s",
    "tooltip_onactivesec_desc": (
        "Defines a monotonic timer relative to the moment the .timer unit itself is activated."
    ),
    "tooltip_onactivesec_example": "30s, 5min, 1h",

    "btn_test_calendar": "Validate (systemd-analyze)",
    "tooltip_test_calendar": "Validate the OnCalendar= expression with 'systemd-analyze calendar' and calculate the next elapse time.",
    "title_calendar_valid": "Valid OnCalendar= Expression",
    "title_calendar_invalid": "Invalid OnCalendar= Expression",

    "lbl_onunitactivesec": "OnUnitActiveSec= (Repeat Interval):",
    "hint_onunitactivesec": "Repeat interval relative to when the target service was last activated (e.g. '1d', '6h', '30min').",
    "tooltip_onunitactivesec_title": "Repeat After Service Activation (OnUnitActiveSec=)",
    "tooltip_onunitactivesec_syntax": "OnUnitActiveSec=1d",
    "tooltip_onunitactivesec_desc": (
        "Defines a monotonic timer relative to when the unit the timer is activating was last activated. "
        "Combining OnBootSec= and OnUnitActiveSec= defines a timer that starts after boot and repeats at regular intervals."
    ),
    "tooltip_onunitactivesec_example": "1d (every 24 hours), 1h (hourly), 30min",

    "lbl_onunitinactivesec": "OnUnitInactiveSec= (After Completion):",
    "hint_onunitinactivesec": "Time relative to when the target service last finished/deactivated (prevents overlap on long tasks).",
    "tooltip_onunitinactivesec_title": "Repeat After Service Deactivation (OnUnitInactiveSec=)",
    "tooltip_onunitinactivesec_syntax": "OnUnitInactiveSec=1h",
    "tooltip_onunitinactivesec_desc": (
        "Defines a monotonic timer relative to when the unit the timer is activating was last deactivated (finished running). "
        "Useful when you want a fixed rest period between the end of one run and the start of the next."
    ),
    "tooltip_onunitinactivesec_example": "1h, 30min",

    # Jitter, Accuracy & Flags
    "lbl_randomizeddelaysec": "RandomizedDelaySec= (Jitter):",
    "hint_randomizeddelaysec": "Adds a random delay between 0 and this span (e.g. '1h', '30min') to spread load spikes.",
    "tooltip_randomizeddelaysec_title": "Randomized Jitter Delay (RandomizedDelaySec=)",
    "tooltip_randomizeddelaysec_syntax": "RandomizedDelaySec=1h",
    "tooltip_randomizeddelaysec_desc": (
        "Delays the timer by a randomly selected, evenly distributed amount of time between 0 and the specified time value "
        "(defaults to 0). Stretches dispatching of similarly configured timer events to prevent resource congestion."
    ),
    "tooltip_randomizeddelaysec_example": "100min, 1h, 15min",

    "lbl_accuracysec": "AccuracySec= (Coalescing):",
    "hint_accuracysec": "Power-saving wake window (default '1min'; set '1s' or '1us' for exact firing time).",
    "tooltip_accuracysec_title": "Timer Elapse Accuracy Window (AccuracySec=)",
    "tooltip_accuracysec_syntax": "AccuracySec=1min",
    "tooltip_accuracysec_desc": (
        "Specifies the accuracy window within which the timer shall elapse (defaults to 1min). systemd coalesces "
        "timer expirations within this window to suppress unnecessary CPU wake-ups and save power. Set to 1us or 1s for tight accuracy."
    ),
    "tooltip_accuracysec_example": "1min (default), 12h, 1s, 1us",

    "chk_persistent": "Persistent=true — Catch up on missed OnCalendar= runs immediately when booting if PC was powered off",
    "tooltip_persistent_title": "Persistent Catch-Up (Persistent=)",
    "tooltip_persistent_syntax": "Persistent=true",
    "tooltip_persistent_desc": (
        "If true, the timestamp when the service unit was last triggered is stored on disk. When the timer is activated, "
        "the service unit is triggered immediately if it would have been triggered at least once while the timer was inactive "
        "(e.g. while the system was powered down). Only affects timers configured with OnCalendar=. Defaults to false."
    ),
    "tooltip_persistent_impact": "Recommended for daily/weekly maintenance & backups",

    "chk_wakesystem": "WakeSystem=true — Resume system from suspend when timer elapses (requires RTC wake support)",
    "tooltip_wakesystem_title": "Wake System From Suspend (WakeSystem=)",
    "tooltip_wakesystem_syntax": "WakeSystem=true",
    "tooltip_wakesystem_desc": (
        "If true, an elapsing timer will cause the system to resume from suspend if the hardware supports RTC wake-up. "
        "Note that this only wakes the system; it does not suspend it again after the service finishes. Defaults to false."
    ),
    "tooltip_wakesystem_impact": "Caution / Power state impact",

    "chk_fixedrandomdelay": "FixedRandomDelay=true — Keep a consistent per-machine RandomizedDelaySec= offset across reboots",
    "tooltip_fixedrandomdelay_title": "Deterministic Random Delay (FixedRandomDelay=)",
    "tooltip_fixedrandomdelay_syntax": "FixedRandomDelay=true",
    "tooltip_fixedrandomdelay_desc": (
        "When enabled alongside RandomizedDelaySec=, the random delay is hashed deterministically from the machine ID "
        "and unit name so the timer always fires at a fixed offset after each calendar event. Recommended by the Arch Wiki "
        "for laptops/desktops that reboot frequently so large RandomizedDelaySec= values do not get endlessly postponed."
    ),

    "chk_onclockchange": "OnClockChange=true — Trigger service when the system wall-clock jumps",
    "tooltip_onclockchange_title": "Trigger on System Clock Jump (OnClockChange=)",
    "tooltip_onclockchange_syntax": "OnClockChange=true",
    "tooltip_onclockchange_desc": (
        "If true, the service unit is triggered whenever the system clock (CLOCK_REALTIME) jumps relative to the "
        "monotonic clock (for example after a manual clock adjustment or large NTP correction)."
    ),

    "chk_ontimezonechange": "OnTimezoneChange=true — Trigger service when the system timezone changes",
    "tooltip_ontimezonechange_title": "Trigger on Timezone Change (OnTimezoneChange=)",
    "tooltip_ontimezonechange_syntax": "OnTimezoneChange=true",
    "tooltip_ontimezonechange_desc": (
        "If true, the service unit is triggered whenever the local system timezone changes."
    ),

    # Timer Action Buttons
    "btn_new_timer_mode": "New Timer Unit",
    "tooltip_new_timer_mode": "Switch the editor to create a brand new .timer unit file.",
    "btn_save_timer": "Save Timer Override & Reload",
    "btn_save_new_timer": "Create Timer Unit & Reload",
    "tooltip_save_timer": "Writes the timer configuration to disk and runs 'systemctl daemon-reload'.",
    "btn_revert_override": "Revert Custom Override",
    "tooltip_revert_override": "Deletes the custom override.conf drop-in file for this timer, restoring vendor defaults.",
    "btn_run_target_now": "Trigger Target Service Now",
    "tooltip_run_target_now": "Immediately executes the service unit activated by this timer (systemctl start <service>).",
    "btn_enable_timer": "Enable Timer (--now)",
    "btn_disable_timer": "Disable Timer",

    # Dialogs & notifications
    "title_no_service_selected": "No Service Selected",
    "msg_select_service_first": "Please select a service from the list first.",
    "title_no_timer_selected": "No Timer Selected",
    "msg_select_timer_first": "Please select a timer from the list first.",
    "title_missing_trigger": "No Timer Trigger Configured",
    "msg_missing_trigger": (
        "Please specify at least one trigger condition (such as OnCalendar=, OnBootSec=, or OnUnitActiveSec=) "
        "so the timer knows when to run."
    ),
    "dialog_exec_title": "Execute: {action}",
    "note_modifies_service": "Modifies state of {service}",
    "note_elevates_scope": "Elevates with pkexec/sudo if system scope",
    "dialog_save_timer_title": "Save systemd Timer Configuration",
    "note_timer_target_path": "Target file: {path}",
    "note_timer_reset_explained": "Includes empty 'OnCalendar=' reset in drop-in override per systemd.timer(5) so new triggers cleanly replace vendor triggers.",
    "note_timer_daemon_reload": "Automatically runs 'systemctl daemon-reload' after writing.",
    "dialog_revert_timer_title": "Revert Timer Override: {unit}",
    "note_revert_timer": "Removes drop-in file {path} and restores package vendor defaults.",
    "title_success": "Success",
    "msg_exec_success": "Executed:\n{command}",
    "msg_timer_saved": "Timer configuration saved to:\n{path}\n\nsystemctl daemon-reload completed.",
    "msg_timer_reverted": "Removed override for {unit} and reloaded systemd.",
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
