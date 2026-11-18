"""User-facing strings for the udev-gui application.

See :mod:`linux_gui_core.i18n` for how localisation works.
"""

from linux_gui_core.i18n import StringTable

EN: dict[str, str] = {
    # Dialog: Advanced attribute selector
    "dlg_adv_title": "Search & Add udev Directive or Preset",
    "lbl_search_attrs": "Search Directives:",
    "placeholder_search_attrs": "Search 'run', 'touchpad', 'libinput', 'wakeup', 'systemd', 'uinput', 'modem'...",
    "group_custom_token": "Or Enter Custom Match / Assignment Token (KEY==\"...\" or KEY=\"...\")",
    "placeholder_custom_token": 'e.g. RUN+="/usr/local/bin/touchpad-tune.sh $devnode" or ATTR{queue/scheduler}="none"',
    "title_no_selection": "No Selection",
    "msg_no_selection": "Please select a directive preset or type a custom token.",

    # Main window
    "window_title": "udev Rule Manager & Builder",
    "preview_title": "Udev Rule Preview",
    "preview_subtitle": "Editing properties below updates the generated udev(7) rule line in real time. Hover any field for man-page documentation.",
    "lbl_rule_file": "Rule File:",
    "btn_new_file": "New File",
    "btn_reload_daemon": "Reload && Trigger (udevadm)",
    "tooltip_reload_daemon_title": "Reload Kernel Udev Rules",
    "tooltip_reload_daemon_cmd": "udevadm control --reload-rules && udevadm trigger",
    "tooltip_reload_daemon_desc": "Instructs systemd-udevd(8) to reload rule files from /etc/udev/rules.d and replays kernel uevents so updated permissions, attributes, and RUN commands take effect immediately.",
    "tooltip_reload_daemon_impact": "Recommended after saving rules",

    # Table columns
    "col_action": "Action",
    "col_subsystem": "Subsystem",
    "col_match": "Match Conditions",
    "col_permissions": "Permissions & Nodes",
    "col_advanced": "Commands (RUN), Power & Attributes",

    # Match conditions group
    "group_match_conditions": "1. Device Match Conditions (Keys using ==)",
    "lbl_subsystem": "SUBSYSTEM==",
    "tooltip_subsystem_title": "Device Subsystem Match (SUBSYSTEM==)",
    "tooltip_subsystem_syntax": 'SUBSYSTEM=="usb" | "hidraw" | "input" | "tty" | "net" | "block"',
    "tooltip_subsystem_desc": "Matches the kernel subsystem of the event device (or parent device when using SUBSYSTEMS==).",

    "lbl_action": "ACTION==",
    "tooltip_action_title": "Event Action Match (ACTION==)",
    "tooltip_action_syntax": 'ACTION=="add" | "change" | "remove" | "bind" | "add|change"',
    "tooltip_action_desc": "Matches the kernel uevent action name. Use 'add' for device plug-in/discovery, or 'add|change' to also re-apply when device state changes.",

    "lbl_vendor": "Vendor ID (idVendor):",
    "placeholder_vendor": "4-digit hex, e.g. 046d or 17ef (from lsusb)",
    "tooltip_vendor_title": "USB / Hardware Vendor ID Match",
    "tooltip_vendor_syntax": 'ATTR{idVendor}=="046d" or ATTRS{idVendor}=="046d"',
    "tooltip_vendor_desc": "Matches the 4-digit lowercase hexadecimal vendor ID exposed in sysfs. Enable 'Match Parent Device Tree (ATTRS)' when matching child nodes like hidraw* or event*.",

    "lbl_product": "Product ID (idProduct):",
    "placeholder_product": "4-digit hex, e.g. c52b or 6042",
    "tooltip_product_title": "USB / Hardware Product ID Match",
    "tooltip_product_syntax": 'ATTR{idProduct}=="c52b" or ATTRS{idProduct}=="c52b"',
    "tooltip_product_desc": "Matches the 4-digit lowercase hexadecimal product ID exposed in sysfs.",

    "lbl_kernel": "KERNEL==",
    "placeholder_kernel": "e.g. hidraw*, event*, ttyUSB*, uinput, nvme0n1",
    "tooltip_kernel_title": "Kernel Device Name Match (KERNEL==)",
    "tooltip_kernel_syntax": 'KERNEL=="hidraw*" | "event*" | "ttyUSB*" | "uinput"',
    "tooltip_kernel_desc": "Matches the kernel name of the event device. Supports shell wildcards (*, ?, []) and alternation (|).",

    "lbl_driver": "DRIVER==",
    "placeholder_driver": "e.g. usbhid, hid-multitouch, i2c_hid_acpi, xhci_hcd",
    "tooltip_driver_title": "Bound Kernel Driver Match (DRIVER==)",
    "tooltip_driver_syntax": 'DRIVER=="hid-multitouch" or DRIVERS=="usb"',
    "tooltip_driver_desc": "Matches the kernel driver bound to the event device (DRIVER==) or searches parent devices upwards (DRIVERS==).",

    "lbl_attr_match": "Property / Attr Match:",
    "placeholder_attr_match": "e.g. *Touchpad*, *vial:*, disk serial, manufacturer, or MAC",
    "tooltip_attr_match_title": "Sysfs Attribute, Serial, or Environment Property Match",
    "tooltip_attr_match_syntax": 'ATTRS{name}=="*Touchpad*" | ATTRS{serial}=="..." | ENV{ID_SERIAL_SHORT}=="..."',
    "tooltip_attr_match_desc": (
        "Matches human-readable input device names (ATTRS{name}), USB hardware serials (ATTRS{serial}), "
        "block disk serial numbers (ENV{ID_SERIAL_SHORT}), manufacturer/product strings, MAC addresses (ATTR{address}), "
        "or sysfs DEVPATH."
    ),

    "chk_parent_attrs": "Search Parent Devices (ATTRS{idVendor} / ATTRS{idProduct})",
    "tooltip_parent_attrs_title": "Search Devpath Upwards (ATTRS vs ATTR)",
    "tooltip_parent_attrs_syntax": 'ATTRS{idVendor}=="...", ATTRS{idProduct}=="..."',
    "tooltip_parent_attrs_desc": "When enabled, udev searches parent devices upwards in sysfs (ATTRS) instead of only the leaf event node (ATTR). Required when matching child subsystems like SUBSYSTEM==\"hidraw\", \"input\", or \"tty\" against parent USB/I2C vendor and product IDs.",

    # Permissions group
    "group_permissions": "2. Device Node Permissions, Ownership & Symlinks (=, +=)",
    "lbl_mode": 'MODE="...":',
    "tooltip_mode_title": "Device Node Permission Mode (MODE=)",
    "tooltip_mode_syntax": 'MODE="0660" | "0666" | "0640" | "0600"',
    "tooltip_mode_desc": "Sets the octal POSIX file permissions on the /dev/ device node, overriding the compiled-in default.",
    "tooltip_mode_impact": "Prefer 0660 + GROUP or TAG+=\"uaccess\" over world-writable 0666",

    "lbl_group": 'GROUP="...":',
    "tooltip_group_title": "Device Node Group Ownership (GROUP=)",
    "tooltip_group_syntax": 'GROUP="plugdev" | "input" | "dialout" | "video" | "uinput"',
    "tooltip_group_desc": "Assigns the Unix group owner for the /dev/ device node.",
    "tooltip_group_impact": "Recommended",

    "lbl_owner": 'OWNER="...":',
    "placeholder_owner": "Optional username (default: root)",
    "tooltip_owner_title": "Device Node User Ownership (OWNER=)",
    "tooltip_owner_syntax": 'OWNER="username"',
    "tooltip_owner_desc": "Assigns a specific Unix user as owner of the /dev/ device node. On multi-user desktop systems, TAG+=\"uaccess\" is generally preferred over hardcoding a single username.",

    "chk_uaccess": 'TAG+="uaccess" (Grant access to active logged-in desktop user)',
    "tooltip_uaccess_title": "systemd-logind Seat User Access Tag (TAG+=\"uaccess\")",
    "tooltip_uaccess_syntax": 'TAG+="uaccess"',
    "tooltip_uaccess_desc": (
        "Instructs systemd-logind to dynamically apply a POSIX ACL granting read/write access to whichever user "
        "is currently active at the physical desktop seat. Standard for HID/QMK keyboards, VR/AR headsets, game controllers, and SDRs.<br><br>"
        "<b>Important (Arch Wiki / systemd):</b> Rule files using <code>TAG+=\"uaccess\"</code> must be lexically ordered before "
        "<code>73-seat-late.rules</code> (for example <code>70-custom-devices.rules</code>) to take effect."
    ),
    "tooltip_uaccess_impact": "Recommended for desktop peripherals (file must be numbered < 73)",

    "lbl_symlink": "SYMLINK+=",
    "placeholder_symlink": "e.g. my_dac or serial/by-id/my_controller",
    "tooltip_symlink_title": "Persistent /dev/ Symlink Alias (SYMLINK+=)",
    "tooltip_symlink_syntax": 'SYMLINK+="custom_name"',
    "tooltip_symlink_desc": "Adds a predictable symlink under /dev/ pointing to the kernel device node (for example /dev/custom_name -> /dev/ttyUSB0). Multiple symlinks can be separated by spaces.",

    # Commands, Services & Power group
    "group_commands_power": "3. Run Commands, Systemd Services & Hardware Power (RUN+=, ENV{}, ATTR{})",
    "lbl_run_cmd": "Execute Command:",
    "placeholder_run_cmd": "e.g. /usr/local/bin/set-touchpad-haptics.sh $devnode  or  /bin/sh -c 'echo 1 > /sys$devpath/...'",
    "tooltip_run_cmd_title": "Execute Program or Command After Rule Processing (RUN+=)",
    "tooltip_run_cmd_syntax": 'RUN+="/path/to/program $devnode" or RUN{builtin}+="kmod load <module>"',
    "tooltip_run_cmd_desc": (
        "Executes an external program (or udev builtin) after all matching rules for the event have been processed. "
        "Commonly used to run hardware configuration tools (such as setting laptop touchpad haptic resistance/click feedback, "
        "sending HID feature reports, or tuning device registers).<br><br>"
        "<b>Substitutions supported:</b> <code>$devnode</code> (<code>%N</code>, full <code>/dev/...</code> path), "
        "<code>$kernel</code> (<code>%k</code>), <code>$sys$devpath</code> (<code>%S%p</code>, full <code>/sys/...</code> path), "
        "<code>$attr{file}</code>.<br><br>"
        "<b>Important (per udev(7)):</b> Must use an absolute executable path (unless in <code>/usr/lib/udev/</code>). "
        "Use single quotes for arguments containing spaces (e.g. <code>/bin/sh -c '...'</code>). Only for short-running foreground tasks; "
        "long-running daemons are killed when the event finishes (use <code>ENV{SYSTEMD_WANTS}+=</code> for background services)."
    ),
    "tooltip_run_cmd_security": "Commands run as root inside the systemd-udevd sandbox (no network or mount access).",

    "lbl_insert_sub": "Insert Token:",
    "sub_placeholder": "Insert $devnode / %k...",
    "tooltip_insert_sub_title": "Insert udev(7) String Substitution into Command",
    "tooltip_insert_sub_syntax": "$devnode (%N) | $kernel (%k) | $sys$devpath (%S%p) | $attr{...}",
    "tooltip_insert_sub_desc": "Appends a standard udev(7) runtime variable substitution to the RUN+= command field.",

    "lbl_systemd_wants": "ENV{SYSTEMD_WANTS}+=",
    "placeholder_systemd_wants": "e.g. my-device-daemon.service (adds TAG+=\"systemd\")",
    "tooltip_systemd_wants_title": "Trigger Systemd Service Unit on Device Event",
    "tooltip_systemd_wants_syntax": 'TAG+="systemd", ENV{SYSTEMD_WANTS}+="my-unit.service"',
    "tooltip_systemd_wants_desc": "Pulls in and starts a systemd service unit when the device becomes available (systemd.device(5), udev(7)). Recommended by udev(7) whenever a device event needs to start a long-running process or access the network.",

    "lbl_wakeup": "ATTR{power/wakeup}=",
    "wakeup_unchanged": "(Unchanged)",
    "wakeup_disabled": 'disabled — Prevent device from waking system from sleep',
    "wakeup_enabled": 'enabled — Allow device to wake system from sleep',
    "tooltip_wakeup_title": "System Sleep / Suspend Wakeup Policy",
    "tooltip_wakeup_syntax": 'ATTR{power/wakeup}="disabled" | "enabled"',
    "tooltip_wakeup_desc": "Writes to the device's power/wakeup sysfs attribute to control whether activity on this device (such as an external mouse, keyboard, or USB receiver) can wake the system from suspend.",

    "lbl_power_control": "ATTR{power/control}=",
    "power_unchanged": "(Unchanged)",
    "power_on": 'on — Disable autosuspend (keep continuously powered)',
    "power_auto": 'auto — Enable kernel runtime power-saving autosuspend',
    "tooltip_power_control_title": "Runtime Power Management / Autosuspend Policy",
    "tooltip_power_control_syntax": 'ATTR{power/control}="on" | "auto"',
    "tooltip_power_control_desc": "Writes to the device's power/control sysfs attribute. Setting 'on' prevents the kernel from autosuspending USB audio interfaces, mice, or serial adapters; setting 'auto' allows runtime power saving when idle.",

    # Extra attributes group
    "group_advanced": "4. Additional Match & Assignment Directives (ATTR{}, ENV{}, OPTIONS+=, IMPORT{}, GOTO/LABEL)",
    "lbl_extra_count": "Additional Directives on Selected Rule:",
    "btn_add_adv": "Search && Add Directive / Preset...",
    "tooltip_add_adv": "Open the searchable udev(7) directive catalog (input/libinput tweaks, sysfs attributes, environment variables, uinput static nodes, ModemManager ignore, and custom tokens).",
    "col_extra_directive": "Directive / Expression",
    "col_extra_action": "Action",
    "btn_remove_extra": "Remove",

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
