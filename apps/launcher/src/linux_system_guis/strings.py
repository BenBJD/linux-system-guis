"""User-facing strings for the Linux System GUIs launcher.

See :mod:`linux_gui_core.i18n` for how localisation works. To add a language,
define a dict with the same keys (partial dicts are fine; missing keys fall back
to English) and register it in ``STRINGS``.
"""

from linux_gui_core.i18n import StringTable

EN: dict[str, str] = {
    "window_title": "Linux System GUIs",
    "header_title": "Linux System GUIs",
    "header_subtitle": "Real-time command previews, dry-run checks, and detailed tooltips.",
    "filter_placeholder": "🔍 Filter tools (e.g. device, logs, sudo, fstab, boot)...",
    "btn_open": "Open",

    # Tool rows
    "tool_device_title": "Device Manager",
    "tool_device_category": "Hardware & Drivers",
    "tool_device_desc": (
        "Inspect system hardware hierarchy, USB vendor & product IDs, PCI slots, loaded kernel drivers, "
        "and DKMS module status with detailed property inspector."
    ),
    "tool_fstab_title": "fstab Editor",
    "tool_fstab_category": "Disks & Mounts",
    "tool_fstab_desc": (
        "Manage /etc/fstab mount points, UUIDs, filesystem options (noatime, nosuid, nofail), "
        "systemd automounts, and test with mount -fa dry runs."
    ),
    "tool_udev_title": "udev Rules Builder",
    "tool_udev_category": "Hardware & Devices",
    "tool_udev_desc": (
        "Create and modify device rules in /etc/udev/rules.d/ with matching vendor IDs, permission modes (0666), "
        "sleep wakeup toggles, uaccess tags, and daemon reloads."
    ),
    "tool_systemd_title": "systemd Services & Timers",
    "tool_systemd_category": "Init & Daemons",
    "tool_systemd_desc": (
        "Explore, start, stop, enable system & user services with friendly status tags (Running, Stopped, "
        "Starts on Boot). Build scheduled timers with OnCalendar expressions."
    ),
    "tool_usermgmt_title": "Users & Groups Security",
    "tool_usermgmt_category": "Access Control",
    "tool_usermgmt_desc": (
        "Manage user accounts, login shells (/bin/bash vs /usr/bin/nologin), and full system group memberships "
        "(vboxusers, ollama, sudo, docker) with real-time usermod command preview."
    ),
    "tool_sudoers_title": "Sudoers Privilege Manager",
    "tool_sudoers_category": "Privilege Delegation",
    "tool_sudoers_desc": (
        "Configure sudoers rules in /etc/sudoers.d/ for users and groups (%wheel). Pick passwordless commands "
        "(NOPASSWD) with automated visudo -c syntax validation."
    ),
    "tool_journal_title": "System Journal & Logs",
    "tool_journal_category": "Diagnostics & Maintenance",
    "tool_journal_desc": (
        "Explore system and service logs with journalctl. Filter by boot sessions (-b), units (-u), "
        "log levels (-p), and vacuum old logs by time or disk size."
    ),
    "tool_sysctl_title": "Kernel Parameters (sysctl)",
    "tool_sysctl_category": "Kernel Tuning",
    "tool_sysctl_desc": (
        "Tune kernel settings (vm.swappiness, BBR TCP, inotify watches, IPv6) with plain-English value "
        "explanations, temporary live changes (sysctl -w), and /etc/sysctl.d/ persistence."
    ),
    "tool_permissions_title": "Advanced Permissions (ACLs & Attr)",
    "tool_permissions_category": "Filesystem Security",
    "tool_permissions_desc": (
        "Manage POSIX Access Control Lists (setfacl / getfacl) for users and groups, and enforce kernel "
        "extended attributes like immutable (+i) via chattr and lsattr."
    ),
    "tool_bootloader_title": "Bootloader & Kernel Args",
    "tool_bootloader_category": "Boot Sequence",
    "tool_bootloader_desc": (
        "Configure kernel boot parameters (quiet, nomodeset, nowatchdog) and timeouts for GRUB "
        "(/etc/default/grub) and systemd-boot with safe configuration regeneration."
    ),
}

STRINGS: dict[str, dict[str, str]] = {
    "en": EN,
}

tr = StringTable(STRINGS)
