"""Unit tests for sysctl presets, backend helpers, and UI."""

import os
from PyQt6.QtWidgets import QApplication, QTableWidget
from linux_gui_core.widgets.preview_banner import MAN_PAGE_GUIDES, MAN_TO_ARCH_WIKI
from sysctl_gui.backend import PRESET_BY_KEY, SYSCTL_PRESETS, SysctlBackend
from sysctl_gui.ui import SysctlMainWindow


def _get_qapp() -> QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_sysctl_presets_catalog():
    assert len(SYSCTL_PRESETS) >= 18
    keys = [p.key for p in SYSCTL_PRESETS]
    assert "vm.swappiness" in keys
    assert "vm.max_map_count" in keys
    assert "net.ipv4.ip_forward" in keys
    assert "net.ipv4.tcp_congestion_control" in keys
    assert "fs.inotify.max_user_watches" in keys
    assert "kernel.sysrq" in keys
    assert "kernel.yama.ptrace_scope" in keys

    # Verify upstream kernel defaults are objective and man pages are registered
    assert PRESET_BY_KEY["vm.swappiness"].kernel_default == "60"
    assert PRESET_BY_KEY["vm.vfs_cache_pressure"].kernel_default == "100"
    assert PRESET_BY_KEY["net.ipv4.ip_forward"].kernel_default == "0"
    assert PRESET_BY_KEY["net.ipv4.tcp_congestion_control"].kernel_default == "cubic"

    for preset in SYSCTL_PRESETS:
        assert preset.kernel_default != ""
        assert preset.man_page in MAN_PAGE_GUIDES
        assert preset.man_page in MAN_TO_ARCH_WIKI
        assert len(preset.value_options) >= 2


def test_sysctl_infer_man_page_and_config_builder():
    assert SysctlBackend.infer_man_page_for_key("vm.swappiness") == "proc_sys_vm(5)"
    assert SysctlBackend.infer_man_page_for_key("net.ipv4.tcp_keepalive_time") == "tcp(7)"
    assert SysctlBackend.infer_man_page_for_key("net.ipv4.icmp_ratelimit") == "icmp(7)"
    assert SysctlBackend.infer_man_page_for_key("net.ipv4.ip_local_port_range") == "ip(7)"
    assert SysctlBackend.infer_man_page_for_key("fs.inotify.max_queued_events") == "inotify(7)"
    assert SysctlBackend.infer_man_page_for_key("fs.file-max") == "proc_sys_fs(5)"
    assert SysctlBackend.infer_man_page_for_key("kernel.pid_max") == "proc_sys_kernel(5)"

    updated = SysctlBackend.build_updated_config_content("vm.swappiness", "10", "")
    assert "vm.swappiness = 10" in updated

    updated2 = SysctlBackend.build_updated_config_content("vm.swappiness", "60", updated)
    assert "vm.swappiness = 60" in updated2
    assert "vm.swappiness = 10" not in updated2


def test_sysctl_live_query():
    # kernel.ostype is universally 'Linux' on all Linux systems
    val = SysctlBackend.get_live_value("kernel.ostype")
    assert val == "Linux"


def test_sysctl_main_window_tooltips_and_shared_inspector():
    _get_qapp()
    win = SysctlMainWindow()

    # Tables must be non-editable
    assert win.tbl_presets.editTriggers() == QTableWidget.EditTrigger.NoEditTriggers
    assert win.tbl_all.editTriggers() == QTableWidget.EditTrigger.NoEditTriggers

    # Every row in tbl_presets has a rich tooltip with a clickable man: link
    assert win.tbl_presets.rowCount() == len(SYSCTL_PRESETS)
    first_tip = win.tbl_presets.item(0, 1).toolTip()
    assert "man:proc_sys_vm(5)" in first_tip
    assert "Default:" in first_tip

    # Selecting a documented value option updates txt_new_val and live preview
    win.cmb_value_options.setCurrentIndex(2)
    chosen_val = win.cmb_value_options.itemData(2)
    assert win.txt_new_val.text() == chosen_val
    assert f"{win.active_key}={chosen_val}" in win.preview_banner.get_text()

    # Reset to kernel default button restores upstream kernel default
    win._fill_kernel_default()
    assert win.txt_new_val.text() == win.selected_preset.kernel_default

    # Selecting an arbitrary parameter from Tab 2 populates the shared inspector
    win._populate_inspector_from_raw_key("net.ipv4.tcp_keepalive_time", "7200")
    assert win.active_key == "net.ipv4.tcp_keepalive_time"
    assert win.txt_new_val.text() == "7200"
    assert "tcp(7)" in win.lbl_param_key.text()
