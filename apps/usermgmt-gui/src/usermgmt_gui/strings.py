"""User-facing strings for the usermgmt-gui application.

See :mod:`linux_gui_core.i18n` for how localisation works.
"""

from linux_gui_core.i18n import StringTable

EN: dict[str, str] = {
    # Create user dialog
    "dlg_create_user_title": "Create New Linux User Account",
    "dlg_create_preview_title": "Useradd Command Preview",
    "dlg_create_preview_subtitle": "Parameters configured below live update the terminal command.",
    "group_account_details": "New Account Details",
    "lbl_username": "Username:",
    "placeholder_username": "e.g. alice, bob, devops",
    "tooltip_username_title": "Account Username",
    "tooltip_username_syntax": "useradd <username>",
    "tooltip_username_desc": "Login identifier for the user. Typically all lowercase letters, numbers, and dashes.",
    "tooltip_username_impact": "Required",
    "tooltip_username_example": "alice",

    "lbl_gecos": "Full Name (GECOS):",
    "placeholder_gecos": "e.g. Alice Smith (Optional)",
    "tooltip_gecos_title": "Comment / Real Name",
    "tooltip_gecos_syntax": '-c "Full Name"',
    "tooltip_gecos_desc": "Informational comment field stored in /etc/passwd.",
    "tooltip_gecos_impact": "Optional",
    "tooltip_gecos_example": "Alice Smith",

    "lbl_shell": "Login Shell:",
    "tooltip_shell_title": "Initial Login Shell",
    "tooltip_shell_syntax": "-s /path/to/shell",
    "tooltip_shell_desc": "Interactive shells (/bin/bash, /usr/bin/zsh) allow terminal login.<br>/usr/bin/nologin prevents interactive terminal login for service accounts.",

    "chk_home": "Create Home Directory (-m)",
    "tooltip_home_title": "Create Home Directory",
    "tooltip_home_syntax": "-m",
    "tooltip_home_desc": "Creates /home/<username> populated with default skeleton files from /etc/skel.",
    "tooltip_home_impact": "Recommended for human users",

    "group_initial_groups": "Initial Group Memberships (Click to add to -G)",
    "tooltip_group_prefix": "Group: {group}",
    "tooltip_group_syntax": "-G {group}",
    "btn_create_account": "Create User Account",

    "title_invalid_username": "Invalid Username",
    "msg_empty_username": "Please enter a username.",
    "msg_invalid_username_regex": "Username must start with a lowercase letter or underscore, and contain only lowercase letters, digits, underscores, or dashes.",

    # Main window
    "window_title": "User & Group Security Manager",
    "preview_title": "Terminal Command Preview",
    "preview_subtitle": "Modifying group checkboxes below dynamically constructs the exact usermod command. Hover to view permission risks.",

    "lbl_filter_accounts": "Filter Accounts:",
    "placeholder_filter_accounts": "Search username or UID...",
    "chk_show_system": "Show System Accounts (UID < 1000)",
    "tooltip_show_system": "Toggle to display low-level system daemon accounts. Advanced users only.",
    "btn_refresh": "🔄 Refresh",

    # Table columns
    "col_username": "Username",
    "col_uid": "UID",
    "col_gecos": "Full Name / GECOS",
    "col_shell": "Login Shell",
    "col_home": "Home Directory",
    "col_groups": "Active Groups",

    # Details panel
    "group_user_profile": "Selected User Profile",
    "tooltip_user_shell_title": "User Login Shell",
    "tooltip_user_shell_syntax": "Interactive or not?",
    "tooltip_user_shell_desc": "<b>Interactive Shells</b> (/bin/bash, /usr/bin/zsh, /usr/bin/fish):<br>Allows a human user to log in interactively via console, terminal, or SSH.<br><br><b>Non-Interactive Shells</b> (/usr/bin/nologin, /usr/sbin/nologin, /bin/false):<br>Prevents interactive login while still allowing the account to own files and run background system services.<br>Protects the system by ensuring service accounts cannot be used to spawn an interactive shell.",
    "tooltip_user_shell_impact": "Security Best Practice",
    "tooltip_user_shell_example": "/bin/bash (or zsh/fish etc.) for humans, /usr/bin/nologin for system services",

    "group_common_groups": "Common Security & Hardware Groups (Click to toggle in real time)",
    "tooltip_member_of": "Member of {group}",

    "group_all_groups": "All Groups",
    "lbl_search_groups": "Search Groups:",
    "placeholder_search_groups": "Filter all groups (e.g. vboxusers, libvirt)...",

    # Bottom action bar
    "btn_create_new_user": "Create New User",
    "btn_delete_user": "Remove Selected User",
    "btn_apply_groups": "Apply Group Changes",

    # Safety dialogs & messages
    "dialog_confirm_create_title": "Confirm User Account Creation",
    "note_create_account": "Creates new account '{username}' with initial shell and groups.",
    "note_elevate_useradd": "Elevates with pkexec to execute useradd.",
    "title_user_created": "User Created",
    "msg_user_created_success": "User '{username}' was created successfully!\n\nCommand executed:\n{command}\n\nTip: You can set their password anytime in terminal via:\nsudo passwd {username}",
    "title_creation_failed": "Creation Failed",
    "msg_creation_failed": "Failed:\n{error}",

    "dialog_delete_title": "Delete User: {username}",
    "note_delete_account": "Deletes account '{username}' and removes home directory.",
    "note_action_irreversible": "THIS ACTION CANNOT BE UNDONE.",
    "title_deleted": "Deleted",
    "msg_deleted_success": "User {username} deleted.",
    "title_delete_failed": "Delete Failed",
    "msg_delete_failed": "Failed:\n{error}",

    "dialog_apply_groups_title": "Apply Group Modifications",
    "note_modify_user_groups": "Modifies group memberships for '{username}'.",
    "note_total_groups": "Total groups assigned: {count}",
    "note_relogin_required": "User must log out and log back in for new group permissions to take effect in active desktop sessions.",
    "title_success": "Success",
    "msg_groups_updated": "Groups updated!\nCommand: {command}",
    "title_update_failed": "Update Failed",
    "msg_update_failed": "Failed:\n{error}",
}

STRINGS: dict[str, dict[str, str]] = {
    "en": EN,
}

tr = StringTable(STRINGS)
