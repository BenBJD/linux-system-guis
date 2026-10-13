"""User-facing strings for the udev-gui application.

See :mod:`linux_gui_core.i18n` for how localisation works.
"""

from linux_gui_core.i18n import StringTable

EN: dict[str, str] = {
    # Dialog: Advanced attribute selector
    "dlg_adv_title": "Search & Add Advanced udev Attribute",
    "lbl_search_attrs": "Search Attributes:",
    "placeholder_search_attrs": "Type 'wakeup', 'power', 'options', 'env'...",
    "group_custom_token": "Or Enter Custom Token",
    "placeholder_custom_token": 'e.g. ATTR{power/wakeup}="disabled" or ENV{MY_VAR}=="1"',
    "title_no_selection": "No Selection",
    "msg_no_selection": "Please select an attribute or type a custom token.",

    # Main window
    "window_title": "udev Rule Manager & Builder",
    "preview_title": "Udev Rule Preview",
    "preview_subtitle": "Editing properties below changes this rule string instantaneously. Hover options to learn what they do.",
    "lbl_rule_file": "Rule File:",
    "btn_new_file": "New File",
    "btn_reload_daemon": "Reload && Trigger (udevadm)",
    "tooltip_reload_daemon_title": "Reload Kernel Udev Rules",
    "tooltip_reload_daemon_cmd": "udevadm control --reload-rules && udevadm trigger",
    "tooltip_reload_daemon_desc": "Notifies systemd-udevd to reload rules from /etc/udev/rules.d and replays device events so new permissions take effect immediately.",
    "tooltip_reload_daemon_impact": "Recommended after changes",

    # Table columns
    "col_action": "Action",
    "col_subsystem": "Subsystem",
    "col_match": "Match Attributes",
    "col_permissions": "Permissions / Mode",
    "col_advanced": "Advanced / Extra Attributes",

    # Match conditions group
    "group_match_conditions": "Device Match Conditions (Keys using ==)",
    "lbl_subsystem": "SUBSYSTEM==",
    "tooltip_subsystem_title": "Subsystem Match",
    "tooltip_subsystem_syntax": 'SUBSYSTEM=="usb"',
    "tooltip_subsystem_desc": "Filters events based on the kernel subsystem providing the device.<br><br><b>Can be blank</b> If blank, this rule matches devices across all kernel subsystems.",

    "lbl_action": "ACTION==",
    "tooltip_action_title": "Action Match",
    "tooltip_action_syntax": 'ACTION=="add"',
    "tooltip_action_desc": "Specifies the kernel event type.<br><br><b>Can be blank</b> If blank, the rule triggers for ALL events (add, remove, change). Specifying 'add' triggers only on device plug-in.",

    "lbl_vendor": "ATTR{idVendor}==",
    "placeholder_vendor": "e.g. 504b or 0483 (find with lsusb)",
    "tooltip_vendor_title": "Vendor ID Match",
    "tooltip_vendor_syntax": 'ATTR{idVendor}=="xxxx"',
    "tooltip_vendor_desc": "4-digit hexadecimal USB Vendor ID from 'lsusb'.<br><br><b>Can be blank</b> If blank, applies to devices from all manufacturers.",

    "lbl_product": "ATTR{idProduct}==",
    "placeholder_product": "e.g. 320f or 5740",
    "tooltip_product_title": "Product ID Match",
    "tooltip_product_syntax": 'ATTR{idProduct}=="xxxx"',
    "tooltip_product_desc": "4-digit hexadecimal USB Product ID.<br><br><b>Can be blank</b> If blank, applies to any model from the specified vendor.",

    "lbl_kernel": "KERNEL==",
    "placeholder_kernel": "e.g. ttyUSB*, hidraw*, sd*",
    "tooltip_kernel_title": "Kernel Name Filter",
    "tooltip_kernel_syntax": 'KERNEL=="ttyUSB*"',
    "tooltip_kernel_desc": "Matches kernel device node name with wildcards (*).<br><br><b>Can be blank</b> If blank, does not restrict by kernel node name.",

    # Permissions group
    "group_permissions": "Permissions & Identifiers (Keys using = or +=)",
    "lbl_mode": 'MODE="...":',
    "tooltip_mode_title": "File Mode Permission",
    "tooltip_mode_syntax": 'MODE="0666"',
    "tooltip_mode_desc": "Sets file permissions for device node.<br><br><b>Can be blank</b> If blank, leaves default kernel permission (usually 0600 root-only).",
    "tooltip_mode_impact": "Caution for 0666",

    "lbl_group": 'GROUP="...":',
    "tooltip_group_title": "Owning Group",
    "tooltip_group_syntax": 'GROUP="plugdev"',
    "tooltip_group_desc": "Assigns device group ownership.<br><br><b>Can be blank</b> If blank, the device node remains owned by the root group.",
    "tooltip_group_impact": "Recommended",

    "chk_uaccess": 'TAG+="uaccess" (Allow active logged-in desktop user)',
    "tooltip_uaccess_title": "systemd User Access Tag",
    "tooltip_uaccess_syntax": 'TAG+="uaccess"',
    "tooltip_uaccess_desc": "Modern systemd mechanism: dynamically grants read/write permissions to whoever is currently active on the desktop seat without group setup.",
    "tooltip_uaccess_impact": "Recommended for desktop Linux",

    "lbl_symlink": "SYMLINK+=",
    "placeholder_symlink": "e.g. my_custom_device",
    "tooltip_symlink_title": "Persistent Symlink Alias",
    "tooltip_symlink_syntax": 'SYMLINK+="custom_device"',
    "tooltip_symlink_desc": "Creates a static alias in /dev/ pointing to this device.<br><br><b>Can be blank</b> If blank, no custom symlink is created.",

    # Extra attributes group
    "group_advanced": "Advanced Attributes & Custom Rules (e.g. Wakeup, Power Management, Options)",
    "lbl_extra_count": "Active Extra Attributes on Selected Rule:",
    "btn_add_adv": "Search && Add Advanced Attribute (e.g. Wakeup, Power)...",
    "tooltip_add_adv": "Search catalog of common advanced attributes including disabling sleep wakeup from keyboards/mice, autosuspend, and custom tokens.",
    "col_extra_directive": "Attribute / Directive",
    "col_extra_action": "Action",
    "btn_remove_extra": "❌ Remove",

    # Bottom action bar
    "btn_add_rule": "Add New Rule",
    "btn_remove_rule": "Remove Selected",
    "btn_save_rules": "Save && Apply Rule File",

    # Cell values
    "val_all": "(all)",
    "val_none": "(none)",

    # Dialogs & safety notices
    "title_no_rule_selected": "No Rule Selected",
    "msg_select_rule_first": "Please select a rule from the table first.",
    "dialog_diff_title": "Inspect Udev File Changes",
    "diff_no_changes": "# No changes",
    "note_managed_file": "⚠️ CAUTION: Managed by package '{pkg}' ({manager}). Editing this file may cause conflict warnings or be overwritten on package upgrade.",
    "note_unmanaged_file": "✓ Unmanaged configuration file. Safe for user edits.",
    "dialog_reload_title": "Reload Udev Rules",
    "note_reload_rules": "Reloads rules into memory in systemd-udevd.",
    "note_trigger_events": "Triggers kernel device event replays so permissions take effect.",
    "title_reloaded": "Reloaded",
    "msg_reload_success": "udev daemon reloaded and events triggered successfully!",
    "title_reload_failed": "Reload Failed",
    "msg_reload_failed": "Failed:\n{error}",
    "dialog_save_title": "Save Udev Rules",
    "note_save_elevated": "Writes file with elevated privileges (pkexec).",
    "note_save_backup": "Automatic timestamped backup will be created.",
    "note_save_pkg_warning": "⚠️ WARNING: This file is tracked by package '{pkg}' ({manager}). Modifying it directly may cause update conflicts!",
    "diff_no_diff": "# No differences detected",
    "title_saved": "Saved",
    "msg_saved_success": "Rules saved!\nBackup: {backup}",
    "title_error_saving": "Error Saving",
    "msg_saved_failed": "Failed:\n{error}",
}

STRINGS: dict[str, dict[str, str]] = {
    "en": EN,
}

tr = StringTable(STRINGS)
