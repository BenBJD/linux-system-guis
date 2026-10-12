"""Unit tests for SafeExecutor commands and backups."""

from linux_gui_core.runner.executor import SafeExecutor


def test_safe_write_dry_run():
    res = SafeExecutor.safe_write_system_file("/etc/fstab", "fake content", dry_run=True)
    assert res.success is True
    assert "[DRY-RUN]" in res.stdout


def test_run_command_unprivileged():
    res = SafeExecutor.run_command(["echo", "hello_linux_guis"], elevated=False)
    assert res.success is True
    assert "hello_linux_guis" in res.stdout.strip()


def test_run_command_nonexistent_binary():
    res = SafeExecutor.run_command(["nonexistent_binary_xyz_12345"], elevated=False)
    assert res.success is False
    assert len(res.stderr) > 0 or not res.success
