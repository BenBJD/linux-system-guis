"""User-facing strings for the device-gui application.

See :mod:`linux_gui_core.i18n` for how localisation works.
"""

from linux_gui_core.i18n import StringTable

EN: dict[str, str] = {
    # Main window & top preview
    "window_title": "Device Manager (Hardware & Drivers)",
    "preview_title": "Linux Device Manager & Hardware Inspector",
    "preview_subtitle": "Explore hardware hierarchy, vendor & product IDs, kernel modules, DKMS drivers, and /dev nodes.",

    # Toolbar
    "lbl_search": "🔍 Search:",
    "placeholder_search": "Filter devices (e.g. nvidia, logitech, audio, 10de, 046d, usb, pci)...",
    "lbl_view": "View:",
    "view_category": "📁 By Category (Standard)",
    "view_connection": "🌲 By Connection (Hierarchy)",
    "btn_expand_all": "➕ Expand All",
    "btn_collapse_all": "➖ Collapse All",
    "btn_refresh": "🔄 Refresh",
    "tooltip_refresh_title": "Rescan Devices",
    "tooltip_refresh_cmd": "udevadm trigger / sysfs rescan",
    "tooltip_refresh_desc": "Reloads the hardware tree from /sys, /proc, and udev to detect newly plugged or removed hardware.",
    "tooltip_refresh_impact": "Safe",
    "btn_export_report": "📄 Export Report",
    "tooltip_report_title": "Hardware Report",
    "tooltip_report_cmd": "inxi / sysfs report",
    "tooltip_report_desc": "Generates a structured text/markdown report of all detected hardware, drivers, and system specs.",
    "tooltip_report_impact": "Safe",

    # Tree & headers
    "lbl_tree_loading": "Loading hardware tree...",
    "lbl_tree_scanning": "Scanning hardware from sysfs, lspci, and lsusb...",
    "lbl_tree_discovered": "Discovered {devices} devices across {categories} categories.",
    "col_device_component": "Device / Component",
    "col_driver": "Driver",
    "col_hw_id_path": "Hardware ID / Path",
    "col_attribute": "Attribute",
    "col_value": "Value",

    # System overview & summary card
    "lbl_system_overview": "System Overview",
    "lbl_hardware_inventory": "Hardware Inventory Summary",
    "lbl_total_devices": "<b>Total Devices:</b>",
    "lbl_processors": "<b>Processors:</b>",
    "lbl_system_memory": "<b>System Memory:</b>",
    "lbl_dkms_drivers": "<b>DKMS Drivers:</b>",
    "lbl_discovered_categories": "Discovered Categories",
    "lbl_tip_card": "💡 <b>Tip:</b> Select any component or peripheral from the device tree on the right to inspect loaded kernel modules, DKMS driver status, vendor & product IDs, /dev nodes, and copy hardware identifiers for udev rules.",

    # Inspector details
    "group_driver_module": "Driver & Kernel Module Status",
    "lbl_driver_status": "<b>Status:</b>",
    "lbl_driver_name": "<b>Driver Name:</b>",
    "val_driverless": "None / Driverless",
    "lbl_module_path": "<b>Module Path:</b>",
    "lbl_ram_footprint": "<b>RAM Footprint:</b>",
    "lbl_used_by": "<b>Used By:</b>",
    "lbl_version": "<b>Version:</b>",
    "lbl_license": "<b>License:</b>",
    "group_hw_identifiers": "Hardware Identifiers",
    "lbl_vendor_id": "<b>Vendor ID:</b>",
    "lbl_product_id": "<b>Product/Device ID:</b>",
    "lbl_subsystem_id": "<b>Subsystem ID:</b>",
    "lbl_pci_slot": "<b>PCI Slot:</b>",
    "lbl_usb_port": "<b>USB Port & Speed:</b>",
    "lbl_device_node": "<b>Device Node:</b>",
    "lbl_sysfs_path": "<b>Sysfs Path:</b>",
    "lbl_modalias": "<b>Modalias:</b>",
    "lbl_power_runtime": "<b>Power Runtime:</b>",
    "val_unknown": "Unknown",
    "val_standard": "Standard",
    "val_unspecified": "unspecified",
    "group_raw_properties": "Raw Sysfs & Device Properties",

    # Educational action buttons
    "btn_copy_hw_id": "📋 Copy HW ID",
    "tooltip_copy_hw_title": "Copy Hardware ID",
    "tooltip_copy_hw_syntax": "ID {vendor}:{product}",
    "tooltip_copy_hw_desc": "Copies '{vendor}:{product}' to clipboard for use in configuration files or search.",
    "btn_copy_modalias": "📋 Copy Modalias",
    "tooltip_copy_mod_title": "Copy Modalias String",
    "tooltip_copy_mod_desc": "Copies the kernel modalias string used by udev and depmod for automatic driver matching.",
    "btn_open_udev": "🛠️ Open in udev Rules",
    "tooltip_open_udev_title": "Create udev Rule",
    "tooltip_open_udev_syntax": 'SUBSYSTEM=="{bus}"',
    "tooltip_open_udev_desc": "Opens the udev Rules Builder tool with this device's subsystem and IDs ready for editing.",
    "btn_reload_driver": "🔄 Reload Driver",
    "tooltip_reload_driver_title": "Reload Kernel Driver Module",
    "tooltip_reload_driver_syntax": "modprobe -r {name} && modprobe {name}",
    "tooltip_reload_driver_desc": "Safely unloads and reloads the '{name}' driver module.",
    "tooltip_reload_driver_impact": "Caution - Device Reset",

    # Copy notifications
    "preview_sub_copied": "Copied {label} to clipboard. Ready to paste into configuration files.",
    "preview_sub_udev_opened": "Opened udev-gui! Copied template rule snippet to clipboard.",
    "title_udev_snippet_copied": "udev Rule Snippet Copied",
    "msg_udev_snippet_copied": "Generated udev rule snippet copied to clipboard:\n\n{snippet}",

    # Driver reload dialog & safety
    "title_no_driver": "No Driver",
    "msg_no_driver": "This device does not have an active kernel module to reload.",
    "preview_sub_reload_cmd": "Command to reload kernel driver module '{name}'.",
    "dialog_reload_driver_title": "Confirm Kernel Driver Reload",
    "note_unload_module": "Unloads kernel module '{name}' using 'modprobe -r'.",
    "note_reload_module": "Reloads module '{name}' immediately using 'modprobe'.",
    "note_device_reset": "Hardware devices using this driver will reset. Active transfers or connections may drop momentarily.",
    "note_root_privileges": "Requires elevated root privileges via pkexec or sudo.",
    "preview_text_reloaded": "Driver '{name}' reloaded successfully.",
    "preview_sub_reload_done": "Driver reload completed without errors.",
    "title_driver_reloaded": "Driver Reloaded",
    "msg_driver_reloaded": "Successfully reloaded kernel driver module '{name}'.",
    "preview_text_reload_err": "Error reloading '{name}'",
    "preview_sub_reload_err": "Driver reload returned an error.",
    "title_driver_reload_notice": "Driver Reload Notice",
    "msg_driver_reload_notice": "Could not reload kernel module '{name}':\n\n{error}\n\nNote: Critical modules (e.g. GPU, NVMe, root USB controllers) often cannot be unloaded while in active use by the desktop environment.",

    # Report dialog
    "dialog_report_title": "Hardware & Driver Report",
    "btn_copy_clipboard": "Copy to Clipboard",
    "val_report_label": "Hardware Report",
}

STRINGS: dict[str, dict[str, str]] = {
    "en": EN,
}

tr = StringTable(STRINGS)
