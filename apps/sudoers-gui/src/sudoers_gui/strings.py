"""User-facing strings for the sudoers-gui application.

See :mod:`linux_gui_core.i18n` for how localisation works.
"""

from linux_gui_core.i18n import StringTable

EN: dict[str, str] = {
    # Main window & preview
    "window_title": "Sudoers Privilege Manager (visudo safe)",
    "preview_title": "Sudoers Config Syntax",
    "preview_subtitle": "Modifying permissions below live updates this rule string. Note: Root permissions are required to inspect system rules.",
    "preview_sub_mod": "Modifying the user, groups, and command permissions below dynamically updates this rule string.",
    "preview_sub_root_req": "⚠️Root access is required to read system sudoers files. Click 'Read as Root' to scan /etc/sudoers and all .d files at once.",
    "preview_sub_dropin": "New drop-in file (not yet created on disk). Configure permissions and click 'Validate && Save File' to apply.",
    "preview_text_root_req": "[ROOT REQUIRED] {path} is protected. Click 'Read as Root' to scan and load contents.",
    "preview_text_root_req_view": "[ROOT REQUIRED] {path} is protected. Click 'Read as Root' to view rules and scan .d files.",
    "preview_text_no_rules": "# No active privilege rules configured in this file.",
    "preview_text_raw_edit": "Editing raw file: {path} ({lines} lines)",

    # Top file bar
    "lbl_sudoers_file": "Sudoers File:",
    "btn_unlock_read": "🔓 Read as Root",
    "tooltip_unlock_read_title": "Batch Read as Root",
    "tooltip_unlock_read_cmd": "pkexec python3",
    "tooltip_unlock_read_desc": "Prompts for root privileges once to load /etc/sudoers, scan all /etc/sudoers.d/ drop-in files, and read their contents.",
    "tooltip_unlock_read_safety": "Safe / Required for inspecting existing rules",
    "btn_refresh_all": "🔄 Refresh (Root)",
    "tooltip_refresh_all": "Re-scan /etc/sudoers and all /etc/sudoers.d/ files to refresh contents.",
    "btn_new_file": "📄 New Drop-in File",
    "tooltip_new_file": "Create a new rule file in /etc/sudoers.d/. Note: sudoers ignores files containing periods (.) or ending in ~.",
    "btn_delete_file": "🗑️ Delete Drop-in",
    "tooltip_delete_file": "Permanently remove the currently selected drop-in file from /etc/sudoers.d/.",
    "btn_validate_syntax": "🧪 Validate with visudo",
    "tooltip_validate_syntax_title": "Syntax Validation",
    "tooltip_validate_syntax_cmd": "visudo -c -f <file>",
    "tooltip_validate_syntax_desc": "Performs strict syntax and parsing validation using the system visudo compiler before applying any changes.",
    "tooltip_validate_syntax_safety": "Strongly Recommended",

    # Tabs
    "tab_visual_builder": "Visual Rule Builder",
    "tab_raw_editor": "📝 Raw File Editor / Comments",
    "lbl_raw_help": "<b>Full File View / Editor:</b> Displays all rules, comments, and Defaults directives. You can edit the text directly here. All changes are validated with <code>visudo -c -f</code> prior to saving.",

    # Table columns
    "col_entity": "Entity (User / Group)",
    "col_hosts": "Target Hosts",
    "col_runas": "Run As Spec",
    "col_password_req": "Password Required?",
    "col_commands": "Permitted Commands",
    "val_nopasswd": "NOPASSWD",
    "val_password_prompt": "Password Prompt",

    # Subject group
    "group_privilege_subject": "Privilege Subject (Who receives elevated access)",
    "rb_user": "Individual User",
    "rb_group": "Group (% prefix)",
    "lbl_account_name": "Account or Group Name:",
    "placeholder_entity": "e.g. wheel, sudo, alice, deployer",
    "tooltip_entity_title": "Privilege Entity",
    "tooltip_entity_syntax": "group or username",
    "tooltip_entity_desc": "The user account or system group granted sudo privileges.",
    "tooltip_entity_impact": "Required",
    "tooltip_entity_example": "wheel (all administrators) or alice",

    # Scope group
    "group_execution_scope": "Execution Scope (Hosts && Run-As User)",
    "lbl_hosts": "Hosts:",
    "tooltip_hosts_title": "Host Specification",
    "tooltip_hosts_syntax": "ALL",
    "tooltip_hosts_desc": "List of network hostnames where this rule applies. Almost always 'ALL' on desktop Linux workstations.",
    "tooltip_hosts_impact": "Standard: ALL",

    "lbl_runas_user": "Run As User:",
    "tooltip_runas_user_title": "Run-As Target User",
    "tooltip_runas_user_syntax": "(ALL) or (root)",
    "tooltip_runas_user_desc": "The target user account that the command can be run as using sudo -u. Defaults to ALL.",
    "tooltip_runas_user_impact": "Standard: ALL",

    "lbl_runas_group": "Run As Group:",
    "tooltip_runas_group_title": "Run-As Target Group",
    "tooltip_runas_group_syntax": "(:ALL)",
    "tooltip_runas_group_desc": "Optional target group specification for sudo -g. Can be left blank or ALL.",

    # Auth & commands group
    "group_auth_commands": "Authentication Policy && Allowed Commands",
    "chk_nopasswd": "NOPASSWD (Allow executing without asking for user's password)",
    "tooltip_nopasswd_title": "Passwordless Execution Tag",
    "tooltip_nopasswd_syntax": "NOPASSWD: ...",
    "tooltip_nopasswd_desc": "Bypasses the sudo password prompt when this rule is invoked.<br><br><b>Security Warning:</b> Use with extreme caution. If this account is compromised, the attacker can execute root commands without needing the user password.",
    "tooltip_nopasswd_impact": "Critical Security Impact",
    "tooltip_nopasswd_example": "NOPASSWD: /usr/bin/systemctl restart nginx",

    "lbl_commands": "Permitted Commands:",
    "placeholder_commands": "e.g. ALL or /usr/bin/systemctl restart nginx, /usr/bin/pacman -Syu",
    "tooltip_commands_title": "Permitted Commands",
    "tooltip_commands_syntax": "ALL or /path/to/binary",
    "tooltip_commands_desc": "Absolute paths to permitted commands, separated by commas. Use 'ALL' for unrestricted root commands.",
    "tooltip_commands_impact": "Restricted paths recommended for specific tasks",

    "lbl_presets": "Insert Preset:",
    "btn_apply_preset": "Insert Command",

    # Bottom action bar
    "btn_add_rule": "➕ Add New Rule",
    "btn_remove_rule": "🗑️ Remove Selected Rule",
    "btn_save_file": "💾 Validate && Save File",
    "tooltip_save_file": "Validates syntax using visudo compiler, creates an automatic backup, and atomically writes with chmod 0440.",

    # Dialogs & safety notices
    "title_parse_error": "Parse Error",
    "msg_parse_error": "Failed to parse sudoers data:\n{error}",
    "title_read_failed": "Read Failed",
    "msg_read_failed": "Could not read sudoers with root:\n{error}",
    "title_confirm_removal": "Confirm Removal",
    "msg_confirm_removal": "Are you sure you want to remove the sudoers privilege rule for:\n\n{rule}?",
    "dialog_new_dropin_title": "Create New Sudoers Drop-in File",
    "dialog_new_dropin_label": "Enter filename for /etc/sudoers.d/:\n(e.g., 99-custom-admin, 10-developers)\n\nNote: Names must NOT contain '.' or end with '~'.",
    "title_invalid_filename": "Invalid Filename",
    "title_action_prohibited": "Action Prohibited",
    "msg_cannot_delete_main": "The main /etc/sudoers file cannot be deleted.",
    "title_confirm_delete_dropin": "Confirm Drop-in File Deletion",
    "msg_confirm_delete_dropin": "Are you sure you want to permanently delete the sudoers drop-in file:\n\n{path}\n\nThis will remove all sudo privileges defined inside it.",
    "title_file_deleted": "File Deleted",
    "msg_dropin_deleted": "Deleted drop-in file:\n{path}",
    "title_deletion_failed": "Deletion Failed",
    "msg_delete_failed": "Could not delete {path}:\n{error}",
    "title_visudo_passed": "visudo Syntax Check Passed",
    "msg_visudo_passed": "visudo syntax validation succeeded!\n\nNo errors or syntax warnings were found in this configuration.",
    "title_visudo_error": "visudo Syntax Error Detected",
    "msg_visudo_error": "visudo reported a syntax error:\n\n{msg}\n\nRule will NOT be saved until corrected to prevent root lockout.",
    "dialog_diff_title": "Inspect Sudoers Changes",
    "diff_no_diff": "# No differences detected",
    "note_verify_visudo": "Syntax will be verified with 'visudo -c -f' before applying.",
    "note_lock_0440": "Permissions will be locked strictly to 0440.",
    "title_refuse_save": "Refusing to Save - visudo Error",
    "msg_refuse_save": "visudo detected an invalid configuration:\n\n{msg}\n\nAborting save to prevent system lockout.",
    "note_save_visudo": "Syntax verified with 'visudo -c -f' (validation passed).",
    "note_save_permissions": "File permissions will be set strictly to 0440 (required by sudo).",
    "note_save_backup": "Timestamped backup will be created before overwriting.",
    "note_primary_modified": "⚠️Primary /etc/sudoers file is being modified.",
    "note_dropin_file": "Drop-in rule file: {path}",
    "note_pkg_managed": "CAUTION: Managed by package '{pkg}'.",
    "dialog_apply_title": "Apply Sudoers Configuration",
    "title_success": "Success",
    "msg_saved_success": "Sudoers configuration successfully saved and validated with chmod 0440!\nPath: {path}",
    "title_save_failed": "Save Failed",
    "msg_save_failed": "Failed:\n{error}",
}

STRINGS: dict[str, dict[str, str]] = {
    "en": EN,
}

tr = StringTable(STRINGS)
