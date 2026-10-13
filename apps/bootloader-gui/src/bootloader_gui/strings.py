"""User-facing strings for the bootloader-gui application.

See :mod:`linux_gui_core.i18n` for how localisation works.
"""

from linux_gui_core.i18n import StringTable

EN: dict[str, str] = {
    # Main window
    "window_title": "Bootloader & Kernel Parameters (GRUB / systemd-boot)",
    "preview_title": "Boot Parameter & Regeneration Command Preview",
    "preview_subtitle": "Modifying kernel arguments below live updates the configuration line and update command.",

    # Selector bar
    "lbl_bootloader_arch": "Bootloader Architecture:",
    "rb_grub": "GRUB (/etc/default/grub)",
    "rb_systemd_boot": "systemd-boot (/efi & /etc/kernel/cmdline)",
    "lbl_detected": "Detected: {details}",
    "btn_unlock_read": "Read Protected ESP as Root",
    "tooltip_unlock_read": "Request root access to read /efi/loader/loader.conf directly.",
    "btn_regen_only": "Run Regeneration Only",
    "tooltip_regen_only": "Runs 'grub-mkconfig' or 'bootctl update' without modifying configuration files.",

    # Path & Status Box
    "group_active_paths": "Active Bootloader Paths & Status",
    "lbl_status_grub": "<b>Config File:</b> <code>/etc/default/grub</code> &nbsp;|&nbsp; <b>Generated Output:</b> <code>/boot/grub/grub.cfg</code> &nbsp;|&nbsp; <b>Regeneration:</b> <code>sudo {regen_cmd}</code>",
    "lbl_status_systemd_boot": "<b>ESP Mount:</b> <code>{esp}</code> &nbsp;|&nbsp; <b>Loader Conf:</b> <code>{loader_conf}</code> &nbsp;|&nbsp; <b>Cmdline File:</b> <code>{cmdline}</code> &nbsp;|&nbsp; <b>Regeneration:</b> <code>sudo {regen_cmd}</code>",

    # Menu & timeout
    "group_boot_menu": "Boot Menu & Timeout Settings",
    "lbl_timeout": "Boot Menu Timeout (Seconds):",
    "tooltip_timeout_title": "Boot Menu Delay",
    "tooltip_timeout_syntax": "timeout 5 or GRUB_TIMEOUT=5",
    "tooltip_timeout_desc": "How long the boot menu countdown displays before automatically booting the default entry. Set to 0 to hide the menu.",
    "tooltip_timeout_impact": "Safe",

    "lbl_default_entry": "Default Entry:",
    "tooltip_default_title": "Default Boot Entry",
    "tooltip_default_syntax": "default <id> or @saved",
    "tooltip_default_desc": "Identifier or index of the default OS to boot.<br><br><b>systemd-boot:</b> Typically filename or machine ID entry, or '@saved'.<br><b>GRUB:</b> Typically '0' or 'saved'.",
    "tooltip_default_impact": "Safe",

    # Arguments
    "group_common_args": "Common Kernel Boot Arguments",
    "tooltip_kernel_arg_prefix": "Kernel Argument: {arg}",
    "group_custom_args": "Custom Extra Kernel Parameters",
    "placeholder_custom_args": "e.g. amdgpu.ppfeaturemask=0xffffffff nvidia-drm.modeset=1 apparmor=1 security=apparmor",
    "tooltip_extra_args_title": "Extra Arguments",
    "tooltip_extra_args_syntax": "Custom flags",
    "tooltip_extra_args_desc": "Space-separated custom kernel arguments appended to the boot command line.",

    # Action bar
    "btn_save": "💾 Save && Regenerate Bootloader",
    "tooltip_save": "Creates backup of configuration files, saves new parameters, and executes the bootloader regeneration command.",

    # Preview subtitles
    "preview_sub_grub": "Modifying kernel arguments updates /etc/default/grub. Regenerate via: sudo {cmd}",
    "preview_sub_systemd_boot": "Updates /etc/kernel/cmdline and loader.conf. Regenerate via: sudo {cmd}",

    # Dialogs & safety notices
    "title_success": "Success",
    "msg_esp_read_success": "Successfully read {path}.",
    "title_read_failed": "Read Failed",
    "msg_read_failed": "Could not read {path}:\n{error}",
    "dialog_diff_title": "Inspect Bootloader Configuration Diff",
    "diff_no_diff": "# No differences detected",
    "note_backup_prior": "Automatic timestamped backups will be created prior to writing.",
    "note_regen_cmd": "Regeneration command: sudo {cmd}",
    "dialog_regen_title": "Regenerate Bootloader",
    "diff_regen_only": "# No configuration file changes.\n# Will execute: sudo {cmd}",
    "note_regen_only": "Runs standard bootloader update to re-index kernels.",
    "msg_regen_success": "Bootloader regenerated successfully!\n\n{output}",
    "title_regen_error": "Regeneration Error",
    "msg_regen_failed": "Failed:\n{error}",
    "dialog_save_title": "Save Configuration & Regenerate Bootloader",
    "note_grub_write": "Writes new parameters to {path}",
    "note_grub_regen": "Executes 'sudo {cmd}' to apply changes to /boot/grub/grub.cfg.",
    "note_systemd_cmdline": "Updates persistent kernel parameters in /etc/kernel/cmdline.",
    "note_systemd_loader": "Updates timeout and default in {path}.",
    "note_systemd_regen": "Executes 'sudo {cmd}' to refresh EFI boot entries.",
    "note_pkg_managed": "Managed by package: {pkg}",
    "title_save_error": "Save Error",
    "msg_save_failed": "Failed writing configuration:\n{error}",
    "msg_cmdline_failed": "Failed writing /etc/kernel/cmdline:\n{error}",
    "title_bootloader_updated": "Bootloader Updated",
    "msg_bootloader_updated": "Configuration saved and bootloader regenerated successfully!\n\nOutput:\n{output}",
    "title_saved_warning": "Saved with Regeneration Warning",
    "msg_saved_warning": "Configuration file was saved, but regeneration reported an error:\n{error}",
}

STRINGS: dict[str, dict[str, str]] = {
    "en": EN,
}

tr = StringTable(STRINGS)
