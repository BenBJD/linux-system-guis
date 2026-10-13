"""User-facing strings for the permissions-gui application.

See :mod:`linux_gui_core.i18n` for how localisation works.
"""

from linux_gui_core.i18n import StringTable

EN: dict[str, str] = {
    # Main window & top bar
    "window_title": "Advanced File Permissions (ACLs & Attributes)",
    "preview_title": "EXACT PERMISSION COMMAND PREVIEW",
    "preview_subtitle": "Modifying ACL entries or attributes below dynamically constructs the exact setfacl or chattr command.",

    "lbl_target_path": "Target Path:",
    "btn_select_file": "📄 Select File...",
    "btn_select_dir": "📁 Select Folder...",
    "lbl_stats_checking": "Checking permissions...",
    "lbl_stats_format": "Target: <b>{path}</b> &nbsp;|&nbsp; Type: {type_str} &nbsp;|&nbsp; Mode: <b>0{mode}</b> &nbsp;|&nbsp; Owner: <b>{owner}</b> &nbsp;|&nbsp; Group: <b>{group}</b>",
    "type_dir": "📁 Directory",
    "type_file": "📄 File",

    # Tabs
    "tab_acls": "👥 Access Control Lists (getfacl / setfacl)",
    "tab_attrs": "🔒 File Attributes (chattr / lsattr)",

    # ACL Tab
    "col_principal_type": "Principal Type",
    "col_target_name": "Target Name",
    "col_permissions": "Permissions (rwx)",
    "col_default_inherited": "Default Inheritance?",
    "val_default_inherited": "Yes (Default Inherited)",
    "val_direct": "Direct",

    "group_grant_acl": "Grant or Modify Extended Access Control Entry (setfacl -m)",
    "rb_user": "User (u:)",
    "rb_group": "Group (g:)",
    "lbl_principal_name": "User or Group Name:",
    "placeholder_principal": "e.g. alice, developers, docker",
    "tooltip_principal_title": "ACL Recipient",
    "tooltip_principal_syntax": "u:username or g:groupname",
    "tooltip_principal_desc": "The specific user account or group granted permissions beyond the base owner.",
    "tooltip_principal_impact": "Required",

    "lbl_perms": "Permissions:",
    "chk_read": "Read (r)",
    "chk_write": "Write (w)",
    "chk_exec": "Execute (x)",

    "chk_default": "Default ACL (-d) - Newly created files inherit this",
    "tooltip_default_title": "Inherited Default ACL",
    "tooltip_default_syntax": "setfacl -d -m ...",
    "tooltip_default_desc": "Only applicable to directories. Files and subfolders created inside will automatically inherit this access entry.",
    "tooltip_default_impact": "Recommended for shared folders",

    "chk_recursive": "Recursive (-R)",
    "tooltip_recursive_title": "Recursive Application",
    "tooltip_recursive_syntax": "-R",
    "tooltip_recursive_desc": "Applies permissions recursively to all subdirectories.",

    "btn_apply_acl": "➕ Grant / Apply ACL Entry",
    "btn_remove_acl": "🗑️ Remove Selected ACL (-x)",
    "tooltip_remove_acl": "Deletes the selected extended ACL entry using 'setfacl -x'.",
    "btn_strip_all_acls": "🧹 Strip All Extended ACLs (-b)",
    "tooltip_strip_all_acls": "Removes all extended ACL entries, restoring standard POSIX permissions.",

    # Attributes Tab
    "group_lsattr": "Current Linux File Attributes (lsattr)",
    "lbl_lsattr_loading": "lsattr output: (loading)",
    "lbl_lsattr_format": "lsattr: {attr}",
    "lbl_attr_expl": "Extended attributes are low-level filesystem flags enforced directly by the Linux kernel (ext4, btrfs, xfs). They can make files completely immutable—preventing accidental deletion even by the root user!",

    "group_configure_attrs": "Configure Kernel Attributes (Click any to toggle)",
    "chk_attr_i": "Immutable (+i) - Cannot be modified, deleted, renamed, or linked, even by root!",
    "tooltip_attr_i_title": "Immutable Flag",
    "tooltip_attr_i_syntax": "sudo chattr +i <file>",
    "tooltip_attr_i_desc": "Locks the file completely against all modifications, renames, and deletions. Even root cannot delete an immutable file without removing the +i flag first.",
    "tooltip_attr_i_impact": "Ultimate Protection against deletion",

    "chk_attr_a": "Append-Only (+a) - Can only be opened in append mode (Ideal for audit logs)",
    "tooltip_attr_a_title": "Append-Only Flag",
    "tooltip_attr_a_syntax": "sudo chattr +a <file>",
    "tooltip_attr_a_desc": "Processes can only append data to the end of the file; existing content cannot be overwritten or deleted.",
    "tooltip_attr_a_impact": "Recommended for Security Logs",

    "chk_attr_d": "No-Dump (+d) - Excluded from backup archives created by dump utility",
    "tooltip_attr_d_title": "No-Dump Flag",
    "tooltip_attr_d_syntax": "chattr +d",
    "tooltip_attr_d_desc": "Prevents file from being backed up by dump utility.",

    "chk_attr_c": "Compressed (+c) - Transparent filesystem compression on disk",
    "tooltip_attr_c_title": "Compressed Flag",
    "tooltip_attr_c_syntax": "chattr +c",
    "tooltip_attr_c_desc": "Requests kernel transparent compression on supported filesystems.",

    "chk_attr_s": "Secure Deletion (+s) - Zeroes out disk blocks upon file deletion",
    "tooltip_attr_s_title": "Secure Deletion Flag",
    "tooltip_attr_s_syntax": "chattr +s",
    "tooltip_attr_s_desc": "Forces kernel to zero out blocks when unlinking.",

    "btn_apply_attrs": "💾 Apply Kernel Attributes (sudo chattr)",

    # Dialogs & notifications
    "dialog_select_file_title": "Select Target File",
    "dialog_select_dir_title": "Select Target Folder",
    "title_not_found": "Not Found",
    "msg_path_not_found": "Path does not exist:\n{path}",
    "title_missing_name": "Missing Name",
    "msg_missing_name": "Please specify a target user or group name.",
    "dialog_apply_acl_title": "Apply Access Control List (ACL)",
    "note_apply_acl": "Grants extended permissions '{perms}' to {p_type}:{name}",
    "note_elevated_pkexec": "Uses elevated privileges via pkexec.",
    "title_acl_applied": "ACL Applied",
    "msg_acl_applied": "Permission successfully granted!\n\n{command}",
    "title_error": "Error",
    "msg_acl_error": "Failed:\n{error}",
    "title_no_selection": "No Selection",
    "msg_select_acl_first": "Please select an ACL entry from the table first.",
    "title_remove_acl": "Remove ACL Entry",
    "msg_confirm_remove_acl": "Remove ACL entry for {p_type}:{name}?",
    "title_failed": "Failed",
    "msg_failed": "Error:\n{error}",
    "title_strip_all_acls": "Strip All ACLs",
    "msg_confirm_strip_all": "Remove ALL extended ACL entries from {path}?",
    "title_no_changes": "No Changes",
    "msg_no_attr_changes": "Attributes match current state; no changes to apply.",
    "dialog_apply_attr_title": "Apply File Attributes",
    "note_mod_kernel_flags": "Modifies low-level kernel filesystem flags.",
    "note_immutable_root": "Setting '+i' will prevent modifications even by root.",
    "title_attrs_applied": "Attributes Applied",
    "msg_attrs_applied": "Updated attributes successfully!\n{command}",
}

STRINGS: dict[str, dict[str, str]] = {
    "en": EN,
}

tr = StringTable(STRINGS)
