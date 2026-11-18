"""User-facing strings for the shared linux_gui_core widgets.

See :mod:`linux_gui_core.i18n` for how localisation works. To add a language,
define a dict with the same keys (partial dicts are fine; missing keys fall back
to English) and register it in ``STRINGS``.
"""

from linux_gui_core.i18n import StringTable

EN: dict[str, str] = {
    # Rich tooltip (widgets/tooltips.py)
    "tooltip_security_label": "Security / Safety:",
    "tooltip_default_label": "Default:",
    "tooltip_recommended_label": "Recommended:",
    "tooltip_blank_label": "If Left Blank:",
    "tooltip_blank_allowed": "✓ Optional (Can be blank)",
    "tooltip_blank_allowed_default_desc": "Omitted when left blank; system or tool default applies.",
    "tooltip_blank_required": "✗ Required (Cannot be blank)",
    "tooltip_blank_required_default_desc": "A value must be provided.",
    "tooltip_example_label": "Example:",
    "tooltip_man_label": "Manual Reference:",
    "tooltip_man_link_text": "man {man_page} — Open in Help Viewer ↗",
    "tooltip_default_impact": "Standard",

    # Live preview banner & man page viewer (widgets/preview_banner.py)
    "banner_default_title": "Live Entry Preview",
    "banner_default_subtitle": "Changes below update this line in real-time. Hover over any checkbox for details.",
    "banner_man_pages_prefix": "Man Pages:",
    "banner_arch_wiki_prefix": "Arch Wiki:",
    "banner_btn_help": "Help && Man Pages",
    "banner_btn_help_tooltip": "Open the Manual Page & Documentation viewer in a tabbed window",
    "banner_btn_copy": "Copy Line",
    "banner_btn_copy_tooltip": "Copy this exact line or command to the clipboard to use in terminal",
    "banner_btn_copied": "Copied!",
    "banner_btn_diff": "Compare Diff",
    "banner_btn_diff_tooltip": "View side-by-side comparison with the existing system configuration",
    "man_window_title": "Help & Linux Manual Pages (man)",
    "man_dialog_title": "Manual Page — {ref}",
    "man_arch_wiki_prefix": "Arch Wiki Practical Guides:",
    "man_intro_banner": (
        "<b>What are Linux 'man' (manual) pages?</b> "
        "They are the official, built-in documentation maintained by the Linux kernel and system tool authors. "
        "The number in parentheses tells you what kind of manual page it is: "
        "<code>(1)</code> User Commands &nbsp;·&nbsp; "
        "<code>(5)</code> Configuration Files &nbsp;·&nbsp; "
        "<code>(7)</code> Concepts &amp; Syntax &nbsp;·&nbsp; "
        "<code>(8)</code> System Administration Tools."
    ),
    "man_search_label": "Search:",
    "man_search_placeholder": "Find option, flag, or keyword in this manual page...",
    "man_btn_next": "Next ↓",
    "man_btn_prev": "Prev ↑",
    "man_btn_open_terminal": ">_ Open in Terminal",
    "man_btn_open_terminal_tooltip": "Launch your system terminal emulator running 'man {cmd}'",
    "man_btn_open_online": "View Online (man.archlinux.org)",
    "man_btn_close": "Close",
    "man_not_installed": (
        "Local man page '{ref}' could not be loaded (or 'man-db' is not installed).\n\n"
        "Click 'View Online (man.archlinux.org)' above to read the manual page in your browser:\n"
        "{url}"
    ),

    # Safety execution dialog (widgets/safety_dialog.py)
    "safety_review_header": "⚠️ <b>Review System Changes</b><br>Target: <code>{target}</code>",
    "safety_protections_heading": "Safety Protections:",
    "safety_preview_label": "Planned Changes / Command Execution:",
    "safety_btn_copy": "📋 Copy Command",
    "safety_btn_apply": "Apply Changes (Requires Root)",

    # Package ownership badge (widgets/package_badge.py)
    "badge_checking": "Checking package status...",
    "badge_unknown_package": "Unknown",
    "badge_managed_by": "Managed by: {package}",
    "badge_managed_tooltip": (
        "<div style='max-width: 320px; line-height: 1.4;'>"
        "<b style='color: #d49a3d;'>Package-Managed File Detected</b><br>"
        "<span style='font-family: monospace;'>{path}</span><br><br>"
        "This file is owned and maintained by the <b>{package}</b> package "
        "(via <i>{manager}</i>).<br><br>"
        "<b>Why this matters:</b><br>"
        "Editing this file directly may be overwritten during future package updates, "
        "or result in configuration merge conflicts (such as .pacnew or .dpkg-dist files). "
        "Consider creating a separate override file if supported (e.g. 99-custom.rules)."
        "</div>"
    ),
    "badge_user_created": "✓ User-Created File",
    "badge_user_created_plain": "User-Created File",
    "badge_default_manager": "system package manager",
    "badge_unmanaged_tooltip": (
        "<div style='max-width: 300px; line-height: 1.4;'>"
        "<b style='color: #57ab5a;'>✓ Unmanaged Configuration File</b><br>"
        "This file is not tracked by {manager}. It was created locally and "
        "can be safely edited or deleted without conflicting with system packages."
        "</div>"
    ),
}

STRINGS: dict[str, dict[str, str]] = {
    "en": EN,
}

tr = StringTable(STRINGS)
