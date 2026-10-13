"""User-facing strings for the sysctl-gui application.

See :mod:`linux_gui_core.i18n` for how localisation works.
"""

from linux_gui_core.i18n import StringTable

EN: dict[str, str] = {
    # Main window
    "window_title": "Kernel Parameters & Tweaks (sysctl)",
    "preview_title": "Sysctl Command Preview",
    "preview_subtitle": "Shows the shell command or sysctl.d configuration line before modification.",

    # Tabs
    "tab_presets": "Curated System Tweaks",
    "tab_all": "Full Parameter Explorer (sysctl -a)",

    # Curated Presets Tab
    "col_category": "Category",
    "col_param_key": "Parameter Key",
    "col_live_val": "Live Kernel Value",
    "col_rec_val": "Recommended Value",
    "col_safety_rating": "Safety Rating",

    "group_param_info": "Selected Kernel Parameter Explanation & Range",
    "lbl_param_key_format": "Key: <code>{key}</code> (Category: {category})",
    "lbl_param_range_format": "Range & Defaults: {range}",
    "lbl_target_value": "New Target Value:",
    "btn_use_recommended": "Use Recommended",

    "btn_apply_live": "Apply Live (sysctl -w)",
    "tooltip_apply_live_title": "Live Memory Change",
    "tooltip_apply_live_cmd": "sudo sysctl -w <key>=<val>",
    "tooltip_apply_live_desc": "Modifies kernel parameter in memory immediately without requiring a reboot. Note: Resets back to default on next reboot unless saved persistently.",
    "tooltip_apply_live_safety": "Safe Temporary Test",

    "btn_save_persistent": "Save Persistent (/etc/sysctl.d/)",
    "tooltip_save_persist_title": "Persistent Configuration",
    "tooltip_save_persist_cmd": "write to /etc/sysctl.d/99-custom.conf && sysctl --system",
    "tooltip_save_persist_desc": "Writes the setting permanently so it persists across reboots, and immediately reloads the system kernel configuration.",
    "tooltip_save_persist_safety": "Permanent Setting",

    # All Parameters Tab
    "lbl_search_param": "Search Parameter:",
    "placeholder_search_param": "Filter any sysctl key (e.g. tcp, inotify, core, bbr)...",
    "btn_query_all": "Query All (sysctl -a)",
    "col_all_name": "Kernel Parameter Name",
    "col_all_val": "Current Live Value",

    # Dialogs & safety notices
    "dialog_live_title": "Apply Live Kernel Parameter",
    "note_live_memory": "Modifies active kernel memory immediately.",
    "note_live_temporary": "Temporary: will reset back to default on next reboot.",
    "note_live_safe": "Safe for testing performance and responsiveness.",
    "title_live_applied": "Live Setting Applied",
    "msg_live_applied": "Kernel parameter updated in memory!\n\n{cmd}",
    "title_failed": "Failed",
    "msg_live_failed": "Error applying setting:\n{error}",

    "dialog_persist_title": "Save Persistent Kernel Parameter",
    "note_persist_write": "Appends/updates '{key} = {val}' in {conf}",
    "note_persist_reload": "Runs 'sysctl --system' to reload all system configuration files.",
    "note_persist_reboot": "Persists across reboots.",
    "title_saved_permanent": "Saved Permanently",
    "msg_saved_permanent": "Setting saved to {conf} and loaded into kernel!",
    "msg_persist_failed": "Error saving setting:\n{error}",
}

STRINGS: dict[str, dict[str, str]] = {
    "en": EN,
}

tr = StringTable(STRINGS)
