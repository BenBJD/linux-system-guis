"""Unit tests for Advanced Permissions (ACLs & Attributes) backend."""

from permissions_gui.backend import PermissionsBackend, ACLEntry


def test_basic_file_stat(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello")
    stat = PermissionsBackend.get_basic_stat(str(f))
    assert "owner" in stat
    assert "group" in stat
    assert "mode" in stat
    assert stat["is_dir"] is False


def test_acl_entry_model():
    entry = ACLEntry(
        is_default=False,
        principal_type="user",
        principal_name="alice",
        permissions="rwx",
    )
    assert entry.principal_name == "alice"
    assert entry.permissions == "rwx"
    assert entry.is_default is False
