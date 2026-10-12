"""Unit tests for /etc/fstab parsing and serialization."""

from fstab_gui.parser import FstabParser, FstabEntry


def test_parse_fstab_file(tmp_path, sample_fstab):
    fstab_file = tmp_path / "fstab"
    fstab_file.write_text(sample_fstab)

    entries = FstabParser.parse_file(str(fstab_file))
    # Should contain comments and mounts
    assert len(entries) > 0

    active_mounts = [e for e in entries if not e.raw_comment]
    assert len(active_mounts) == 5

    # Check root mount
    root_entry = next(e for e in active_mounts if e.mount_point == "/")
    assert root_entry.fs_spec == "/dev/nvme0n1p2"
    assert root_entry.vfstype == "ext4"
    assert "noatime" in root_entry.options
    assert root_entry.dump == 0
    assert root_entry.passno == 1

    # Check network CIFS mount with x-systemd.automount
    nas_entry = next(e for e in active_mounts if e.mount_point == "/mnt/nas")
    assert "x-systemd.automount" in nas_entry.options
    assert nas_entry.vfstype == "cifs"


def test_fstab_entry_to_line():
    entry = FstabEntry(
        fs_spec="UUID=abcd-1234",
        mount_point="/data",
        vfstype="ext4",
        options=["noatime", "nodev", "nosuid"],
        dump=0,
        passno=2,
    )
    line = entry.to_line()
    assert "UUID=abcd-1234" in line
    assert "/data" in line
    assert "ext4" in line
    assert "noatime,nodev,nosuid" in line
    assert line.endswith("0 2")
