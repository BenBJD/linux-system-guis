"""Global test fixtures and configuration for linux-system-guis test suite."""

import os
import pytest
from PyQt6.QtWidgets import QApplication
from linux_gui_core.theme import apply_theme

# Ensure Qt runs headlessly in offscreen mode
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    """Initializes and returns the shared QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    apply_theme(app)
    return app


@pytest.fixture
def sample_fstab():
    """Sample /etc/fstab text containing various filesystem specifications."""
    return (
        "# /etc/fstab: static file system information.\n"
        "# <file system> <mount point>   <type>  <options>       <dump>  <pass>\n"
        "UUID=1234-5678 /boot/efi       vfat    umask=0077      0       2\n"
        "/dev/nvme0n1p2 /               ext4    noatime,errors=remount-ro 0 1\n"
        "UUID=abcd-ef01 /home           btrfs   subvol=@home,compress=zstd 0 2\n"
        "# Network mount\n"
        "//192.168.1.100/share /mnt/nas cifs   credentials=/etc/smbpass,noauto,x-systemd.automount 0 0\n"
        "tmpfs          /tmp            tmpfs   defaults,noatime,mode=1777 0 0\n"
    )


@pytest.fixture
def sample_sudoers():
    """Sample /etc/sudoers content with user, group, and NOPASSWD directives."""
    return (
        "# /etc/sudoers\n"
        "Defaults        env_reset\n"
        "Defaults        mail_badpass\n"
        "\n"
        "root ALL=(ALL:ALL) ALL\n"
        "%wheel ALL=(ALL:ALL) ALL\n"
        "%admin ALL=(ALL) ALL\n"
        "alice ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx\n"
        "@includedir /etc/sudoers.d\n"
    )


@pytest.fixture
def sample_udev():
    """Sample udev rules file."""
    return (
        "# 99-custom-devices.rules\n"
        'SUBSYSTEM=="usb", ATTR{idVendor}=="1234", ATTR{idProduct}=="5678", MODE="0666", TAG+="uaccess"\n'
        'ACTION=="add", SUBSYSTEM=="input", ATTR{name}=="My Keyboard", ATTR{power/wakeup}="disabled"\n'
    )


@pytest.fixture
def sample_grub():
    """Sample /etc/default/grub content."""
    return (
        'GRUB_DEFAULT=0\n'
        'GRUB_TIMEOUT=5\n'
        'GRUB_DISTRIBUTOR="Arch"\n'
        'GRUB_CMDLINE_LINUX_DEFAULT="loglevel=3 quiet"\n'
        'GRUB_CMDLINE_LINUX=""\n'
    )
