"""User-facing strings for the shared linux_gui_core widgets.

See :mod:`linux_gui_core.i18n` for how localisation works. To add a language,
define a dict with the same keys (partial dicts are fine; missing keys fall back
to English) and register it in ``STRINGS``.
"""

from linux_gui_core.i18n import StringTable

EN: dict[str, str] = {
    # Rich tooltip (widgets/tooltips.py)
    "tooltip_security_label": "Security / Safety:",
    "tooltip_example_label": "Example:",
    "tooltip_default_impact": "Standard",

    # Live preview banner (widgets/preview_banner.py)
    "banner_default_title": "Live Entry Preview",
    "banner_default_subtitle": "Changes below update this line in real-time. Hover over any checkbox for details.",
    "banner_btn_copy": "Copy Line",
    "banner_btn_copy_tooltip": "Copy this exact line or command to the clipboard to use in terminal",
    "banner_btn_copied": "Copied!",
    "banner_btn_diff": "Compare Diff",
    "banner_btn_diff_tooltip": "View side-by-side comparison with the existing system configuration",

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
