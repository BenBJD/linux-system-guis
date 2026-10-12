"""Unit tests for sysctl presets and parameter operations."""

from sysctl_gui.backend import SYSCTL_PRESETS, SysctlBackend


def test_sysctl_presets_catalog():
    assert len(SYSCTL_PRESETS) >= 8
    keys = [p.key for p in SYSCTL_PRESETS]
    assert "vm.swappiness" in keys
    assert "net.ipv4.ip_forward" in keys
    assert "fs.inotify.max_user_watches" in keys


def test_sysctl_live_query():
    # kernel.ostype is universally 'Linux' on all Linux systems
    val = SysctlBackend.get_live_value("kernel.ostype")
    assert val == "Linux"
