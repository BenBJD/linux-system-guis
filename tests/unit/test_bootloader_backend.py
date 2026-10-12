"""Unit tests for Bootloader configuration parser and serializer."""

from bootloader_gui.backend import BootloaderBackend, BootloaderConfig


def test_parse_grub_config(tmp_path, sample_grub):
    grub_file = tmp_path / "grub"
    grub_file.write_text(sample_grub)

    cfg = BootloaderBackend.load_grub_config(str(grub_file))
    assert cfg.timeout == 5
    assert cfg.default_entry == "0"
    assert "quiet" in cfg.kernel_params
    assert "loglevel=3" in cfg.kernel_params


def test_serialize_grub_config():
    original = 'GRUB_TIMEOUT=5\nGRUB_DEFAULT=0\nGRUB_CMDLINE_LINUX_DEFAULT="quiet"\n'
    cfg = BootloaderConfig(
        raw_content=original,
        timeout=10,
        default_entry="saved",
        kernel_params=["quiet", "nomodeset", "nowatchdog"],
    )
    new_text = BootloaderBackend.serialize_grub_config(cfg)
    assert "GRUB_TIMEOUT=10" in new_text
    assert 'GRUB_DEFAULT="saved"' in new_text or "GRUB_DEFAULT=saved" in new_text
    assert "nomodeset" in new_text
    assert "nowatchdog" in new_text
