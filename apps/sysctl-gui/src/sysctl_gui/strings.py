"""User-facing strings for the sysctl-gui application.

See :mod:`linux_gui_core.i18n` for how localisation works.
"""

from linux_gui_core.i18n import StringTable

EN: dict[str, str] = {
    # Main window
    "window_title": "Kernel Parameters & Tunables (sysctl)",
    "preview_title": "Sysctl Command & Configuration Preview",
    "preview_subtitle": "Shows the live sysctl command and persistent /etc/sysctl.d/ configuration line before applying.",

    # Top drop-in configuration bar
    "lbl_target_conf": "Target Drop-in File (/etc/sysctl.d/):",
    "btn_new_file": "New Drop-in File",
    "btn_reload_system": "Reload All (sysctl --system)",
    "dialog_new_file_title": "New sysctl.d Drop-in File",
    "dialog_new_file_prompt": "Enter filename (e.g. 99-sysctl.conf or 90-network.conf):",

    # Tabs
    "tab_presets": "Documented Kernel Parameters",
    "tab_all": "Full Parameter Explorer (sysctl -a)",

    # Documented Parameters Tab filter bar
    "lbl_category_filter": "Category:",
    "opt_all_categories": "All Categories",
    "lbl_preset_search": "Filter:",
    "placeholder_preset_search": "Filter by parameter key, title, or man page (e.g. swappiness, tcp, inotify, bpf)...",
    "btn_refresh_live": "Refresh Live Values",

    # Documented Parameters Table columns
    "col_category": "Category",
    "col_param_key": "Parameter Key",
    "col_live_val": "Live Kernel Value",
    "col_kernel_default": "Kernel Default",
    "col_valid_range": "Valid Values & Man Page",

    # Shared Bottom Parameter Inspector & Value Editor
    "group_param_info": "Selected Kernel Parameter Reference & Value Editor",
    "lbl_param_key_format": "Key: <code>{key}</code> · Category: <b>{category}</b> · Reference: <code>{man_page}</code>",
    "lbl_param_range_format": "Live Value: <b>{live}</b> · Kernel Default: <b>{default}</b> · Valid Range: {range}",
    "lbl_documented_values": "Documented Values:",
    "opt_select_documented": "Select a documented value or type below...",
    "lbl_target_value": "Target Value:",
    "btn_use_default": "Reset to Kernel Default",
    "btn_use_live": "Use Live Value",

    "btn_apply_live": "Apply Live (sysctl -w)",
    "tooltip_apply_live_title": "Apply Runtime Kernel Parameter (Temporary)",
    "tooltip_apply_live_cmd": "sudo sysctl -w <key>=<value>",
    "tooltip_apply_live_desc": "Writes the new value directly to /proc/sys/ in active kernel memory without rebooting. Temporary changes revert to defaults on the next reboot unless saved to /etc/sysctl.d/.",
    "tooltip_apply_live_safety": "Does not modify files on disk; resets on reboot.",

    "btn_save_persistent": "Save Persistent (/etc/sysctl.d/)",
    "tooltip_save_persist_title": "Save Persistent Configuration (/etc/sysctl.d/)",
    "tooltip_save_persist_cmd": "write to /etc/sysctl.d/*.conf && sudo sysctl --system",
    "tooltip_save_persist_desc": "Writes 'key = value' to the selected /etc/sysctl.d/ drop-in configuration file so it is applied automatically by systemd-sysctl at boot, then runs 'sysctl --system' to apply it immediately.",
    "tooltip_save_persist_safety": "Modifies /etc/sysctl.d/ configuration file and reloads system tunables.",

    # All Parameters Tab
    "lbl_search_param": "Search Parameter:",
    "placeholder_search_param": "Filter any sysctl key (e.g. vm., net.ipv4.tcp, fs.inotify, kernel.)...",
    "btn_query_all": "Query All (sysctl -a)",
    "col_all_name": "Kernel Parameter Name",
    "col_all_val": "Current Live Value",
    "col_all_man": "Subsystem Man Page",
    "desc_custom_param": (
        "Live kernel parameter queried via sysctl -a from /proc/sys/. Consult {man_page} and proc_sys(5) "
        "in the Help Window for authoritative upstream kernel documentation before modifying."
    ),

    # Dialogs & safety notices
    "dialog_diff_title": "Inspect Configuration Changes",
    "note_diff_preview": "Previewing pending change to {conf} (Dry Run).",
    "dialog_reload_title": "Reload All sysctl.d Configurations",
    "note_reload_desc": "Runs 'sysctl --system' to reload all /etc/sysctl.d/*.conf and /usr/lib/sysctl.d/*.conf files in lexicographical order.",
    "title_reloaded": "Kernel Configurations Reloaded",
    "msg_reloaded": "Successfully executed 'sysctl --system'.",
    "dialog_live_title": "Apply Live Kernel Parameter",
    "note_live_memory": "Modifies active kernel memory (/proc/sys/) immediately.",
    "note_live_temporary": "Temporary: resets to default on the next reboot unless saved persistently.",
    "note_live_safe": "Useful for testing runtime behavior before committing to /etc/sysctl.d/.",
    "title_live_applied": "Live Setting Applied",
    "msg_live_applied": "Kernel parameter updated in memory:\n\n{cmd}",
    "title_failed": "Operation Failed",
    "msg_live_failed": "Error applying kernel parameter:\n{error}",

    "dialog_persist_title": "Save Persistent Kernel Parameter",
    "note_persist_write": "Writes '{key} = {val}' to {conf}",
    "note_persist_reload": "Runs 'sysctl --system' to reload all system configuration files.",
    "note_persist_reboot": "Persists across reboots via systemd-sysctl.service.",
    "title_saved_permanent": "Saved Permanently",
    "msg_saved_permanent": "Setting saved to {conf} and loaded into kernel.",
    "msg_persist_failed": "Error saving setting:\n{error}",
    "title_empty_value": "Value Required",
    "msg_empty_value": "Please enter a non-empty value for the selected kernel parameter.",
}

STRINGS: dict[str, dict[str, str]] = {
    "en": EN,
}

tr = StringTable(STRINGS)
