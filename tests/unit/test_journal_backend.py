"""Unit tests for journalctl command builder and vacuum operations."""

from journal_gui.backend import JournalBackend


def test_build_query_cmd_flags():
    # Test building specific query flags
    cmd = JournalBackend.build_query_cmd(
        boot="0",
        unit="nginx.service",
        priority="err",
        grep="timeout",
        lines=150,
        user_mode=False,
    )
    assert cmd[0] == "journalctl"
    assert "-b" in cmd and "0" in cmd
    assert "-u" in cmd and "nginx.service" in cmd
    assert "-p" in cmd and "err" in cmd
    assert "-g" in cmd and "timeout" in cmd
    assert "-n" in cmd and "150" in cmd


def test_build_query_cmd_user_mode():
    cmd = JournalBackend.build_query_cmd(
        boot="all",
        unit="",
        priority="all",
        user_mode=True,
    )
    assert "--user" in cmd
    assert "-b" not in cmd
    assert "-p" not in cmd
