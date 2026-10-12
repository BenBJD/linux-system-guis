"""Unit tests for systemd manager state translations and unit parsing."""

from systemd_gui.manager import SystemdManager


def test_translate_runtime_status():
    assert "Running" in SystemdManager._translate_runtime_status("active", "running", "loaded")
    assert "Failed" in SystemdManager._translate_runtime_status("failed", "failed", "loaded")
    assert "Stopped" in SystemdManager._translate_runtime_status("inactive", "dead", "loaded")
    assert "one-shot" in SystemdManager._translate_runtime_status("active", "exited", "loaded")


def test_translate_boot_status():
    assert "Runs on boot" in SystemdManager._translate_boot_status("enabled")
    assert "Manual" in SystemdManager._translate_boot_status("disabled")
    assert "Blocked" in SystemdManager._translate_boot_status("masked")
