"""User-facing strings for the fstab-gui application.

See :mod:`linux_gui_core.i18n` for how localisation works.
"""

from linux_gui_core.i18n import StringTable

EN: dict[str, str] = {
    # Dialog: Advanced mount options
    "dlg_adv_title": "Search & Add Advanced / systemd Mount Option",
    "lbl_search_options": "Search Options:",
    "placeholder_search_adv": "Search 'automount', 'network', 'timeout', 'compress', 'btrfs'...",
    "group_custom_option": "Or Enter Custom Mount Option",
    "placeholder_custom_option": "e.g. x-systemd.automount or subvol=@var or umask=077",
    "title_no_selection": "No Selection",
    "msg_no_option_selected": "Please choose an option from the list or enter a custom one.",

    # Main window
    "window_title": "fstab Editor - {path}",
    "preview_title": "/etc/fstab entry preview",
    "preview_subtitle": "The line below updates as you toggle options. Hover over options for safety & command tooltips.",
    "lbl_target_file": "Target File: <code>{path}</code>",

    # Table columns
    "col_device": "Device / UUID",
    "col_mount_point": "Mount Point",
    "col_filesystem": "Filesystem",
    "col_options": "Options",
    "col_dump": "Dump",
    "col_pass": "Pass",

    # Selected entry properties
    "group_entry_properties": "Selected Entry Properties",
    "lbl_device": "Device / UUID / LABEL:",
    "placeholder_device": "e.g. UUID=3a7b-..., LABEL=Data, /dev/sdb1",
    "tooltip_fs_spec_title": "Filesystem Specification",
    "tooltip_fs_spec_syntax": "UUID=... or LABEL=... or /dev/...",
    "tooltip_fs_spec_desc": "Identifies the disk partition. Using UUID is strongly recommended because device names like /dev/sda can change across reboots.<br><br><b>Cannot be blank</b>. Must identify a partition.",
    "tooltip_fs_spec_safety": "Recommended: UUID",
    "tooltip_fs_spec_example": "UUID=1234-ABCD",

    "lbl_mount_point": "Mount Point:",
    "placeholder_mount_point": "e.g. /, /home, /mnt/storage",
    "tooltip_mount_title": "Mount Point",
    "tooltip_mount_syntax": "/path/to/folder",
    "tooltip_mount_desc": "The directory in the root hierarchy where the filesystem is made accessible (or 'none' for swap).<br><br><b>Cannot be blank</b>.",
    "tooltip_mount_safety": "Required directory",
    "tooltip_mount_example": "/mnt/data",

    "lbl_fs_type": "Filesystem Type:",
    "lbl_dump": "Dump:",
    "tooltip_dump_title": "Dump Flag",
    "tooltip_dump_syntax": "0 or 1",
    "tooltip_dump_desc": "Used by dump utility to backup filesystem. Rarely used on modern Linux; defaults to 0.<br><br><b>Cannot be blank</b>",

    "lbl_pass": "Pass:",
    "tooltip_pass_title": "Fsck Pass Order",
    "tooltip_pass_syntax": "0 (skip), 1 (root partition), 2 (other partitions)",
    "tooltip_pass_desc": "Determines the order in which filesystem checks are done at reboot time.<br><br><b>Cannot be blank</b>.",
    "tooltip_pass_safety": "Safer to use 1 for root (/), 2 for other local drives, 0 for swap/network. Use 0 for xfs and btrfs mounts.",

    # Common options group
    "group_common_options": "Common Mount Options (Click any to toggle in real time)",
    "tooltip_mount_option_prefix": "Mount Option: {opt}",

    # Advanced options group
    "group_adv_options": "Advanced Mount Options (e.g. Automount, Network Dependencies, Timeouts)",
    "lbl_adv_count": "Active Advanced / Custom Options:",
    "btn_add_advanced": "Add Advanced Option",
    "tooltip_add_advanced": "Search a catalog of mount options including systemd automount, network targets, idle timeouts, and Btrfs subvolumes.",
    "col_adv_directive": "Option Directive",
    "col_adv_action": "Action",
    "btn_remove_adv": "❌ Remove",

    # Bottom action bar
    "btn_add_entry": "➕ Add New Entry",
    "btn_remove_selected": "🗑️ Remove Selected",
    "btn_dry_run": "🧪 Dry Run (mount -fa)",
    "tooltip_dry_run": "Runs 'mount -fa' (fake mount) to validate the fstab syntax without actually mounting filesystems.",
    "btn_apply": "💾 Apply && Save to /etc/fstab",
    "tooltip_apply": "Inspects diff, creates automatic backup, and writes changes with elevated privileges.",

    # Dialogs & notifications
    "title_no_entry_selected": "No Entry Selected",
    "msg_select_entry_first": "Please select an entry in the fstab table first.",
    "title_confirm_removal": "Confirm Removal",
    "msg_confirm_removal": "Are you sure you want to remove the mount entry for:\n\n{mount_point} ({fs_spec})?",
    "title_no_changes": "No Changes",
    "msg_no_changes": "No changes detected compared to the current file.",
    "dialog_diff_title": "Inspect /etc/fstab Diff",
    "note_backup_created": "Automatic backup will be created before saving.",
    "note_review_root_boot": "Review that the root (/) and /boot entries are intact.",
    "title_dry_run_passed": "Dry-Run Check Passed",
    "msg_dry_run_passed": "Command 'mount -fa' reported no syntax or mounting errors.",
    "title_dry_run_warning": "Dry-Run Warning",
    "msg_dry_run_warning": "mount -fa reported:\n{output}",
    "dialog_apply_title": "Apply /etc/fstab Modifications",
    "note_timestamped_backup": "Timestamped backup will be created in /etc/fstab.bak.<timestamp>",
    "note_elevated_privileges": "Uses elevated privileges via pkexec.",
    "diff_no_diff": "# No differences detected",
    "title_success": "Success",
    "msg_apply_success": "/etc/fstab updated successfully!\nBackup: {backup}",
    "title_error_applying": "Error Applying Changes",
    "msg_apply_error": "Failed:\n{error}",
}

STRINGS: dict[str, dict[str, str]] = {
    "en": EN,
}

tr = StringTable(STRINGS)
