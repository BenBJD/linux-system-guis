"""User-facing strings for the journal-gui application.

See :mod:`linux_gui_core.i18n` for how localisation works.
"""

from linux_gui_core.i18n import StringTable

EN: dict[str, str] = {
    # Main window & top bar
    "window_title": "System Journal & Log Explorer (journalctl)",
    "preview_title": "Journalctl Command Preview",
    "preview_subtitle": "Modifying dropdowns and filters below immediately constructs the exact terminal command.",
    "lbl_scope": "Scope:",
    "rb_system": "System Logs (All Daemons & Kernel)",
    "rb_user": "User Session (--user)",
    "btn_refresh": "🔄 Refresh Logs",

    # Tabs
    "tab_logs": "📜 Log Explorer",
    "tab_maint": "🧹 Maintenance & Disk Cleanup",

    # Filter controls
    "group_filters": "Filter Criteria (Narrow down your logs)",
    "lbl_boot": "Boot Session (-b):",
    "tooltip_boot_title": "Boot Session Filter",
    "tooltip_boot_syntax": "-b 0 or -b -1",
    "tooltip_boot_desc": "Limits logs to a specific boot. '0' is the current running system session, '-1' is the previous boot before the last restart.",
    "tooltip_boot_impact": "Standard: 0",
    "tooltip_boot_example": "journalctl -b -1 (check why PC crashed on last boot)",

    "lbl_priority": "Log Priority (-p):",
    "lbl_service_unit": "Service Unit (-u):",
    "placeholder_unit": "e.g. NetworkManager.service, sshd.service, bluetooth.service",
    "tooltip_unit_title": "Service Filter",
    "tooltip_unit_syntax": "-u <service_name>",
    "tooltip_unit_desc": "Isolates logs produced by a single systemd service unit. Leave blank to view all system activity.",
    "tooltip_unit_impact": "Safe",
    "tooltip_unit_example": "journalctl -u docker.service",

    "lbl_search_pattern": "Search Pattern (-g):",
    "placeholder_grep": "Filter text string (e.g. failed, disconnect, timeout)...",
    "tooltip_grep_title": "Pattern Match",
    "tooltip_grep_syntax": "-g <pattern>",
    "tooltip_grep_desc": "Regular expression or substring filter for journal messages.",
    "tooltip_grep_impact": "Safe",

    "lbl_line_limit": "Line Limit (-n):",
    "tooltip_lines_title": "Entry Limit",
    "tooltip_lines_syntax": "-n <count>",
    "tooltip_lines_desc": "Controls how many recent entries to display.",

    "btn_apply_filters": "🔍 Apply Filters && Search",
    "lbl_status_ready": "Ready",
    "lbl_status_showing": "Showing {count} log entries",
    "btn_copy_logs": "📋 Copy Visible Logs",
    "btn_export_logs": "💾 Export to .log File",

    # Maintenance tab
    "group_usage": "Current Journal Disk Usage",
    "lbl_usage_calc": "Calculating journal disk usage...",
    "lbl_usage_desc": "Systemd stores system logs under /var/log/journal. Over months, archived logs can consume multiple gigabytes of disk space. You can safely vacuum old logs without affecting system stability.",

    "group_vacuum_time": "Cleanup by Retention Age (--vacuum-time)",
    "btn_vac_7d": "🧹 Vacuum older than 7 Days (--vacuum-time=7d)",
    "tooltip_vac_time_title": "Vacuum by Time",
    "tooltip_vac_time_syntax": "journalctl --vacuum-time=7d",
    "tooltip_vac_time_desc": "Deletes archived logs older than 7 days.",
    "tooltip_vac_time_impact": "Safe / Recommended",
    "btn_vac_14d": "🧹 Vacuum older than 2 Weeks (--vacuum-time=14d)",
    "btn_vac_30d": "🧹 Vacuum older than 1 Month (--vacuum-time=30d)",
    "btn_vac_custom_time": "🧹 Custom Age Vacuum...",

    "group_vacuum_size": "Cleanup by Maximum Disk Size (--vacuum-size)",
    "btn_vac_200m": "📦 Vacuum to max 200 MB (--vacuum-size=200M)",
    "btn_vac_500m": "📦 Vacuum to max 500 MB (--vacuum-size=500M)",
    "btn_vac_1g": "📦 Vacuum to max 1 GB (--vacuum-size=1G)",
    "btn_vac_custom_sz": "📦 Custom Size Vacuum...",

    # Boot sessions
    "opt_current_boot": "Current Boot (0)",
    "opt_prev_boot": "Previous Boot (-1)",
    "opt_all_boot": "All Boot History",

    # Dialogs & notifications
    "title_copied": "Copied",
    "msg_copied": "Visible log entries copied to clipboard.",
    "dialog_save_logs_title": "Save Journal Logs",
    "dialog_save_logs_filter": "Log Files (*.log);;All Files (*)",
    "title_exported": "Exported",
    "msg_exported": "Logs successfully saved to {path}",
    "dialog_confirm_vacuum_title": "Confirm Journal Vacuum Maintenance",
    "note_vacuum_purge": "Safely purges old archived logs to free disk space.",
    "note_vacuum_active_safe": "Active log entries from the current boot session are never deleted.",
    "note_vacuum_root": "Requires elevated root privileges.",
    "title_vacuum_completed": "Vacuum Completed",
    "msg_vacuum_completed": "Vacuum finished!\n\n{output}",
    "title_vacuum_failed": "Vacuum Failed",
    "msg_vacuum_failed": "Failed:\n{error}",
    "dialog_custom_age_title": "Custom Vacuum Age",
    "dialog_custom_age_label": "Enter retention threshold (e.g. 5d, 2weeks, 1month):",
    "dialog_custom_size_title": "Custom Vacuum Size",
    "dialog_custom_size_label": "Enter maximum journal size (e.g. 300M, 2G):",
}

STRINGS: dict[str, dict[str, str]] = {
    "en": EN,
}

tr = StringTable(STRINGS)
