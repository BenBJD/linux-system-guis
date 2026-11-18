"""Live preview banner widget and tabbed embedded-terminal Man Page Help Window."""

import html
import os
import re
import shutil
import subprocess
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QFont, QGuiApplication, QTextDocument
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from linux_gui_core.strings import tr


# Beginner-friendly guide mapping man page references to:
# (Short Tab Label, Plain-English Summary for Inexperienced Users)
MAN_PAGE_GUIDES: dict[str, tuple[str, str]] = {
    # Device Manager
    "lspci(8)": (
        "lspci(8) · PCI Hardware",
        "<b>PCI Hardware Inspector (<code>lspci</code>):</b> Lists all internal components connected to your motherboard's PCI/PCIe buses, such as graphics cards (GPUs), network/Wi-Fi adapters, NVMe SSD controllers, and audio chips, and shows which Linux kernel driver is handling each device.",
    ),
    "lsusb(8)": (
        "lsusb(8) · USB Devices",
        "<b>USB Device Inspector (<code>lsusb</code>):</b> Lists all USB root hubs and plugged-in USB peripherals (keyboards, mice, webcams, flash drives, audio interfaces) along with their 4-digit hexadecimal Vendor and Product IDs (<code>ID xxxx:yyyy</code>).",
    ),
    "modinfo(8)": (
        "modinfo(8) · Driver Info",
        "<b>Kernel Driver Module Info (<code>modinfo</code>):</b> Displays detailed metadata about a Linux kernel driver module (<code>.ko</code> file), including its description, version, license, file path, configurable parameters, and hardware <code>modalias</code> patterns.",
    ),
    "modprobe(8)": (
        "modprobe(8) · Load/Unload Drivers",
        "<b>Kernel Driver Loader (<code>modprobe</code>):</b> Loads (<code>modprobe &lt;driver&gt;</code>) or unloads (<code>modprobe -r &lt;driver&gt;</code>) kernel driver modules while automatically resolving any other modules the driver depends on.",
    ),
    "udevadm(8)": (
        "udevadm(8) · Device Events",
        "<b>udev Device Manager Tool (<code>udevadm</code>):</b> Controls the runtime device manager daemon, queries device attributes from the kernel database, and reloads or replays hardware events (<code>udevadm control --reload-rules &amp;&amp; udevadm trigger</code>) so permission changes apply immediately.",
    ),
    "sysfs(5)": (
        "sysfs(5) · /sys Device Tree",
        "<b>Kernel Device Hierarchy (<code>/sys</code>):</b> Explains the virtual <code>/sys</code> filesystem where the Linux kernel exposes live hardware topology, power management settings, and driver bindings as readable files and folders.",
    ),
    # fstab Mount Manager
    "fstab(5)": (
        "fstab(5) · /etc/fstab Format",
        "<b>Filesystem Mount Table (<code>/etc/fstab</code>):</b> Defines which disk partitions, NVMe drives, swap spaces, and network shares are mounted automatically at boot time. Each line has 6 fields: Device (<code>fs_spec</code>), Mount Point (<code>fs_file</code>), Filesystem Type (<code>fs_vfstype</code>), Options (<code>fs_mntops</code>), Dump (<code>fs_freq</code>), and Check Order (<code>fs_passno</code>).",
    ),
    "mount(8)": (
        "mount(8) · Mount Options",
        "<b>Filesystem Mount Command &amp; Options (<code>mount</code>):</b> Documents the <code>mount</code> command and all general and filesystem-specific mount options (such as <code>defaults</code>, <code>noatime</code>, <code>nofail</code>, <code>ro</code>, <code>uid=</code>, and <code>gid=</code>).",
    ),
    "systemd.mount(5)": (
        "systemd.mount(5) · systemd Mounts",
        "<b>systemd Mount Units:</b> Explains how systemd automatically translates <code>/etc/fstab</code> entries into mount units at boot, and documents special <code>x-systemd.*</code> mount options like on-demand automounting (<code>x-systemd.automount</code>) and device timeouts.",
    ),
    "fsck(8)": (
        "fsck(8) · Disk Check",
        "<b>Filesystem Consistency Check (<code>fsck</code>):</b> Verifies and repairs filesystems during boot according to the 6th column (<code>Pass</code>) of <code>/etc/fstab</code> (<code>1</code> for root <code>/</code>, <code>2</code> for other checked local disks, <code>0</code> to skip checking).",
    ),
    # udev Rule Builder
    "udev(7)": (
        "udev(7) · udev Rules Syntax",
        "<b>Dynamic Device Management Rules (<code>udev</code>):</b> Complete guide to writing <code>/etc/udev/rules.d/*.rules</code> files. Explains how match keys (like <code>SUBSYSTEM==</code>, <code>ATTR{idVendor}==</code>) identify hardware and assignment keys (like <code>MODE=</code>, <code>GROUP=</code>, <code>TAG+=\"uaccess\"</code>) grant user permissions.",
    ),
    "systemd-udevd.service(8)": (
        "systemd-udevd(8) · Device Daemon",
        "<b>Device Event Daemon (<code>systemd-udevd</code>):</b> The background system service that listens to kernel hardware plug/unplug events (uevents), creates device nodes in <code>/dev/</code>, and applies your udev rules.",
    ),
    # Systemd Service & Timer Manager
    "systemctl(1)": (
        "systemctl(1) · Service Control",
        "<b>Systemd Control Tool (<code>systemctl</code>):</b> The primary command used to start, stop, restart, enable on boot, disable, mask, and inspect Linux background services (<code>.service</code>) and scheduled timers (<code>.timer</code>).",
    ),
    "systemd.service(5)": (
        "systemd.service(5) · Service Units",
        "<b>Service Unit Configuration:</b> Documents how <code>.service</code> unit files define background processes, including startup commands (<code>ExecStart=</code>), service types (<code>Type=</code>), automatic restart policies (<code>Restart=</code>), and sandboxing.",
    ),
    "systemd.timer(5)": (
        "systemd.timer(5) · Timer Units",
        "<b>Scheduled Timer Configuration:</b> Documents <code>.timer</code> units (systemd's modern replacement for cron jobs). Explains wall-clock schedules (<code>OnCalendar=</code>), monotonic delays (<code>OnBootSec=</code>, <code>OnUnitActiveSec=</code>), catch-up behavior (<code>Persistent=</code>), and jitter (<code>RandomizedDelaySec=</code>).",
    ),
    "systemd.time(7)": (
        "systemd.time(7) · Time & Calendar Syntax",
        "<b>Time Span &amp; Calendar Expression Reference:</b> Explains how to write time durations (such as <code>15min</code>, <code>2h 30min</code>, <code>7d</code>) and calendar schedules (such as <code>daily</code>, <code>*-*-* 02:00:00</code>, <code>Mon..Fri 09:00</code>) used in timer settings.",
    ),
    "systemd.unit(5)": (
        "systemd.unit(5) · Unit Structure & Overrides",
        "<b>Common Unit Structure &amp; Drop-in Overrides:</b> Explains sections shared by all systemd units (<code>[Unit]</code>, <code>[Install]</code>) and how <code>.d/override.conf</code> drop-in files customize vendor units safely without editing system package files.",
    ),
    # Sysctl Tweaker
    "sysctl(8)": (
        "sysctl(8) · Kernel Tunables Tool",
        "<b>Runtime Kernel Parameter Tool (<code>sysctl</code>):</b> Reads and modifies live Linux kernel parameters in memory (such as virtual memory swap behavior, network buffers, and security restrictions) and reloads persistent config files (<code>sysctl --system</code>).",
    ),
    "sysctl.conf(5)": (
        "sysctl.conf(5) · Config Syntax",
        "<b>Sysctl Configuration File Format:</b> Documents the <code>parameter = value</code> syntax used in sysctl configuration files to set kernel parameters at boot.",
    ),
    "sysctl.d(5)": (
        "sysctl.d(5) · /etc/sysctl.d/ Drop-ins",
        "<b>Sysctl Drop-in Directory (<code>/etc/sysctl.d/</code>):</b> Explains how modular <code>*.conf</code> files in <code>/etc/sysctl.d/</code> override default kernel settings and in what order they are applied at startup.",
    ),
    "proc_sys(5)": (
        "proc_sys(5) · /proc/sys/ Reference",
        "<b>Kernel Tunables Reference (<code>/proc/sys/</code>):</b> Authoritative documentation for the virtual <code>/proc/sys/</code> directory tree (<code>vm.*</code>, <code>net.*</code>, <code>kernel.*</code>, <code>fs.*</code>) where the Linux kernel exposes runtime settings.",
    ),
    "proc_sys_vm(5)": (
        "proc_sys_vm(5) · Virtual Memory Tunables",
        "<b>Virtual Memory Subsystem (<code>/proc/sys/vm/</code>):</b> Documents kernel memory management parameters including swap reclaim preference (<code>vm.swappiness</code>), filesystem cache reclaim (<code>vm.vfs_cache_pressure</code>), dirty page writeback thresholds (<code>vm.dirty_ratio</code>, <code>vm.dirty_background_ratio</code>), and memory map limits (<code>vm.max_map_count</code>).",
    ),
    "proc_sys_kernel(5)": (
        "proc_sys_kernel(5) · Core Kernel & Security",
        "<b>Core Kernel &amp; Security Parameters (<code>/proc/sys/kernel/</code>):</b> Documents general kernel behavior and security hardening tunables such as Magic SysRq key bitmasks (<code>kernel.sysrq</code>), kernel log access (<code>kernel.dmesg_restrict</code>), kernel pointer hiding (<code>kernel.kptr_restrict</code>), Yama ptrace restrictions (<code>kernel.yama.ptrace_scope</code>), and NMI watchdog.",
    ),
    "proc_sys_fs(5)": (
        "proc_sys_fs(5) · Filesystem Tunables",
        "<b>Filesystem &amp; File Descriptor Limits (<code>/proc/sys/fs/</code>):</b> Documents system-wide file handle limits (<code>fs.file-max</code>), hard/symbolic link protection (<code>fs.protected_hardlinks</code>, <code>fs.protected_symlinks</code>), and filesystem sub-directories such as <code>/proc/sys/fs/inotify/</code>.",
    ),
    "proc_sys_net(5)": (
        "proc_sys_net(5) · Networking Tunables",
        "<b>Networking Subsystem Overview (<code>/proc/sys/net/</code>):</b> Documents core networking queue parameters (<code>net.core.*</code>), socket listen backlog limits (<code>net.core.somaxconn</code>), default packet queuing disciplines (<code>net.core.default_qdisc</code>), and protocol-specific directories.",
    ),
    "tcp(7)": (
        "tcp(7) · TCP Protocol & sysctl",
        "<b>TCP Protocol &amp; Kernel Variables (<code>net.ipv4.tcp_*</code>):</b> Authoritative reference for TCP socket behavior and <code>/proc/sys/net/ipv4/tcp_*</code> parameters, including congestion control algorithms (<code>tcp_congestion_control</code>), TCP Fast Open (<code>tcp_fastopen</code>), SYN cookies (<code>tcp_syncookies</code>), and keepalive timers.",
    ),
    "ip(7)": (
        "ip(7) · IPv4 Protocol & Routing",
        "<b>IPv4 Protocol &amp; Routing Variables (<code>net.ipv4.*</code>):</b> Documents IPv4 packet forwarding (<code>net.ipv4.ip_forward</code>), Reverse Path Filtering (<code>rp_filter</code>), ICMP redirect acceptance (<code>accept_redirects</code>), and unprivileged ping group ranges (<code>ping_group_range</code>).",
    ),
    "icmp(7)": (
        "icmp(7) · ICMP & Ping Variables",
        "<b>ICMP Protocol &amp; Echo Settings (<code>net.ipv4.icmp_*</code>):</b> Documents how the Linux kernel handles ICMP control messages, including ignoring echo requests/pings (<code>icmp_echo_ignore_all</code>, <code>icmp_echo_ignore_broadcasts</code>) and rate limiting.",
    ),
    "inotify(7)": (
        "inotify(7) · File Monitoring Limits",
        "<b>Filesystem Event Monitoring API (<code>fs.inotify.*</code>):</b> Explains how desktop file managers, IDEs, and build tools watch directories for changes, and documents the kernel limits in <code>/proc/sys/fs/inotify/</code> (<code>max_user_watches</code>, <code>max_user_instances</code>, <code>max_queued_events</code>).",
    ),
    # User & Group Security Manager
    "usermod(8)": (
        "usermod(8) · Modify User Account",
        "<b>Modify User Account (<code>usermod</code>):</b> Updates an existing user account's supplementary group memberships (<code>-G</code>), login shell (<code>-s</code>), home directory, or lock status.",
    ),
    "useradd(8)": (
        "useradd(8) · Create User Account",
        "<b>Create New User (<code>useradd</code>):</b> Creates a new Linux user account, initializes their <code>/home/&lt;username&gt;</code> directory from <code>/etc/skel</code> (<code>-m</code>), and sets their login shell and initial groups.",
    ),
    "userdel(8)": (
        "userdel(8) · Delete User Account",
        "<b>Delete User Account (<code>userdel</code>):</b> Removes a user account from system databases and optionally deletes their home directory and mail spool (<code>-r</code>).",
    ),
    "passwd(5)": (
        "passwd(5) · /etc/passwd Format",
        "<b>User Account Database (<code>/etc/passwd</code>):</b> Explains the 7 colon-separated fields stored for every account: username, password placeholder, UID, primary GID, GECOS comment/full name, home directory, and login shell.",
    ),
    "group(5)": (
        "group(5) · /etc/group Format",
        "<b>System Group Database (<code>/etc/group</code>):</b> Explains how Linux security and hardware permission groups (such as <code>wheel</code>, <code>sudo</code>, <code>docker</code>, <code>dialout</code>, and <code>input</code>) and their member lists are stored.",
    ),
    "nologin(8)": (
        "nologin(8) · Non-Interactive Shell",
        "<b>Polite Login Refusal Shell (<code>/usr/bin/nologin</code>):</b> A special shell assigned to background daemon/service accounts so they can own files and run services without allowing anyone to log into an interactive terminal as that account.",
    ),
    # Sudoers Privilege Manager
    "sudoers(5)": (
        "sudoers(5) · Sudo Policy Syntax",
        "<b>Sudo Security Policy Format (<code>/etc/sudoers</code>):</b> Authoritative reference for sudo privilege rules (<code>user HOST=(RUNAS_USER:RUNAS_GROUP) NOPASSWD: COMMANDS</code>), group prefixes (<code>%wheel</code>), and <code>/etc/sudoers.d/</code> drop-in files.",
    ),
    "visudo(8)": (
        "visudo(8) · Safe Syntax Checker",
        "<b>Sudoers Syntax Validator (<code>visudo</code>):</b> Compiles and checks sudoers files for syntax errors (<code>visudo -c -f</code>) before saving so a typo never locks you out of administrative access.",
    ),
    "sudo(8)": (
        "sudo(8) · Run Command as Root",
        "<b>Execute Command as Superuser (<code>sudo</code>):</b> Explains how permitted users run administrative commands as <code>root</code> (or another user via <code>sudo -u</code>) and how credential caching works.",
    ),
    # Journal & Log Explorer
    "journalctl(1)": (
        "journalctl(1) · Query System Logs",
        "<b>Systemd Log Viewer (<code>journalctl</code>):</b> Queries and filters logs collected by systemd-journald. Explains boot session filtering (<code>-b</code>), severity levels (<code>-p</code>), unit filters (<code>-u</code>), regex search (<code>-g</code>), and disk cleanup (<code>--vacuum-time</code>, <code>--vacuum-size</code>).",
    ),
    "journald.conf(5)": (
        "journald.conf(5) · Log Storage Config",
        "<b>Journal Service Configuration:</b> Documents <code>/etc/systemd/journald.conf</code> settings that control persistent log storage, maximum disk usage (<code>SystemMaxUse=</code>), and log retention.",
    ),
    "systemd-journald.service(8)": (
        "systemd-journald(8) · Logging Daemon",
        "<b>System Logging Daemon:</b> Explains how the <code>systemd-journald</code> background service captures, indexes, and stores structured logs from the kernel, system services, and applications.",
    ),
    # Advanced File Permissions
    "acl(5)": (
        "acl(5) · POSIX ACLs Overview",
        "<b>Access Control Lists Overview:</b> Beginner-friendly guide to POSIX ACLs, which extend standard Linux <code>rwx</code> owner/group/other permissions so you can grant access on a file or folder to multiple specific users or groups.",
    ),
    "setfacl(1)": (
        "setfacl(1) · Modify File ACLs",
        "<b>Set File Access Control Lists (<code>setfacl</code>):</b> Grants or modifies ACL entries (<code>-m u:alice:rw</code>), sets inherited directory defaults (<code>-d</code>), applies recursively (<code>-R</code>), or removes extended ACLs (<code>-x</code>, <code>-b</code>).",
    ),
    "getfacl(1)": (
        "getfacl(1) · View File ACLs",
        "<b>Read File Access Control Lists (<code>getfacl</code>):</b> Displays the owner, group, effective permission mask, and all access and default ACL entries configured on a file or directory.",
    ),
    "chattr(1)": (
        "chattr(1) · Kernel Inode Flags",
        "<b>Change File Inode Attributes (<code>chattr</code>):</b> Sets low-level kernel filesystem flags such as Immutable (<code>+i</code>, preventing modification or deletion even by root), Append-Only (<code>+a</code>), and No-Dump (<code>+d</code>).",
    ),
    "lsattr(1)": (
        "lsattr(1) · List Inode Flags",
        "<b>List File Inode Attributes (<code>lsattr</code>):</b> Displays the low-level filesystem attribute flags (<code>i</code>, <code>a</code>, <code>d</code>, <code>e</code>, <code>c</code>, <code>s</code>) currently active on files or directories.",
    ),
    # Bootloader & Kernel Parameters
    "kernel-command-line(7)": (
        "kernel-command-line(7) · Boot Parameters",
        "<b>Kernel Boot Command-Line Parameters:</b> Reference for startup arguments passed to the Linux kernel by the bootloader (such as <code>quiet</code>, <code>splash</code>, <code>nomodeset</code>, <code>loglevel=</code>, and systemd boot flags).",
    ),
    "bootctl(1)": (
        "bootctl(1) · UEFI & systemd-boot",
        "<b>UEFI Firmware &amp; Bootloader Control (<code>bootctl</code>):</b> Inspects UEFI boot status, manages EFI boot entries, and updates <code>systemd-boot</code> binaries in the EFI System Partition (<code>bootctl update</code>).",
    ),
    "loader.conf(5)": (
        "loader.conf(5) · systemd-boot Config",
        "<b>systemd-boot Menu Configuration (<code>loader.conf</code>):</b> Documents configuration options in <code>/efi/loader/loader.conf</code> (or <code>/boot/loader/loader.conf</code>), including menu countdown delay (<code>timeout</code>) and default OS entry (<code>default</code>).",
    ),
    "grub-mkconfig(8)": (
        "grub-mkconfig(8) · GRUB Generator",
        "<b>GRUB Configuration Generator (<code>grub-mkconfig</code>):</b> Reads settings and kernel arguments from <code>/etc/default/grub</code>, scans installed Linux kernels, and writes the final <code>/boot/grub/grub.cfg</code> boot menu.",
    ),
}

SECTION_DESCRIPTIONS: dict[str, str] = {
    "1": "Section 1 · User Command / CLI Utility",
    "5": "Section 5 · Configuration File Format",
    "7": "Section 7 · System Concept & Syntax Overview",
    "8": "Section 8 · System Administration & Root Tool",
}

# Curated mapping from man page references to the 1 or 2 most relevant Arch Wiki guides
MAN_TO_ARCH_WIKI: dict[str, list[tuple[str, str]]] = {
    # Device & Driver Manager
    "lspci(8)": [
        ("Kernel module", "https://wiki.archlinux.org/title/Kernel_module"),
        ("udev", "https://wiki.archlinux.org/title/Udev"),
    ],
    "lsusb(8)": [
        ("udev", "https://wiki.archlinux.org/title/Udev"),
        ("Kernel module", "https://wiki.archlinux.org/title/Kernel_module"),
    ],
    "modinfo(8)": [
        ("Kernel module", "https://wiki.archlinux.org/title/Kernel_module"),
    ],
    "modprobe(8)": [
        ("Kernel module", "https://wiki.archlinux.org/title/Kernel_module"),
    ],
    "sysfs(5)": [
        ("udev", "https://wiki.archlinux.org/title/Udev"),
        ("Kernel module", "https://wiki.archlinux.org/title/Kernel_module"),
    ],
    # fstab & Disk Mount Manager
    "fstab(5)": [
        ("Fstab", "https://wiki.archlinux.org/title/Fstab"),
        ("Persistent block device naming", "https://wiki.archlinux.org/title/Persistent_block_device_naming"),
    ],
    "mount(8)": [
        ("Fstab", "https://wiki.archlinux.org/title/Fstab"),
        ("File systems", "https://wiki.archlinux.org/title/File_systems"),
    ],
    "systemd.mount(5)": [
        ("Fstab: Automount with systemd", "https://wiki.archlinux.org/title/Fstab#Automount_with_systemd"),
        ("systemd", "https://wiki.archlinux.org/title/Systemd"),
    ],
    "fsck(8)": [
        ("fsck", "https://wiki.archlinux.org/title/Fsck"),
        ("Fstab", "https://wiki.archlinux.org/title/Fstab"),
    ],
    # udev Rule Builder
    "udev(7)": [
        ("udev", "https://wiki.archlinux.org/title/Udev"),
        ("Wakeup triggers", "https://wiki.archlinux.org/title/Power_management/Wakeup_triggers"),
    ],
    "udevadm(8)": [
        ("udev", "https://wiki.archlinux.org/title/Udev"),
    ],
    "systemd-udevd.service(8)": [
        ("udev", "https://wiki.archlinux.org/title/Udev"),
    ],
    # Systemd Service & Timer Manager
    "systemctl(1)": [
        ("systemd", "https://wiki.archlinux.org/title/Systemd"),
        ("systemd/Timers", "https://wiki.archlinux.org/title/Systemd/Timers"),
    ],
    "systemd.service(5)": [
        ("systemd", "https://wiki.archlinux.org/title/Systemd"),
    ],
    "systemd.timer(5)": [
        ("systemd/Timers", "https://wiki.archlinux.org/title/Systemd/Timers"),
        ("systemd", "https://wiki.archlinux.org/title/Systemd"),
    ],
    "systemd.time(7)": [
        ("systemd/Timers", "https://wiki.archlinux.org/title/Systemd/Timers"),
    ],
    "systemd.unit(5)": [
        ("systemd: Drop-in files", "https://wiki.archlinux.org/title/Systemd#Drop-in_files"),
    ],
    # Sysctl Tweaker
    "sysctl(8)": [
        ("sysctl", "https://wiki.archlinux.org/title/Sysctl"),
    ],
    "sysctl.conf(5)": [
        ("sysctl", "https://wiki.archlinux.org/title/Sysctl"),
    ],
    "sysctl.d(5)": [
        ("sysctl", "https://wiki.archlinux.org/title/Sysctl"),
    ],
    "proc_sys(5)": [
        ("sysctl", "https://wiki.archlinux.org/title/Sysctl"),
    ],
    "proc_sys_vm(5)": [
        ("sysctl: Virtual memory", "https://wiki.archlinux.org/title/Sysctl#Virtual_memory"),
        ("Swap: Swappiness", "https://wiki.archlinux.org/title/Swap#Swappiness"),
    ],
    "proc_sys_kernel(5)": [
        ("sysctl", "https://wiki.archlinux.org/title/Sysctl"),
        ("Security: Kernel hardening", "https://wiki.archlinux.org/title/Security#Kernel_hardening"),
    ],
    "proc_sys_fs(5)": [
        ("sysctl", "https://wiki.archlinux.org/title/Sysctl"),
    ],
    "proc_sys_net(5)": [
        ("sysctl: Improving performance", "https://wiki.archlinux.org/title/Sysctl#Improving_performance"),
    ],
    "tcp(7)": [
        ("sysctl: TCP/IP stack hardening", "https://wiki.archlinux.org/title/Sysctl#TCP/IP_stack_hardening"),
    ],
    "ip(7)": [
        ("sysctl: Networking", "https://wiki.archlinux.org/title/Sysctl#Networking"),
    ],
    "icmp(7)": [
        ("sysctl: TCP/IP stack hardening", "https://wiki.archlinux.org/title/Sysctl#TCP/IP_stack_hardening"),
    ],
    "inotify(7)": [
        ("sysctl", "https://wiki.archlinux.org/title/Sysctl"),
    ],
    # User & Group Security Manager
    "usermod(8)": [
        ("Users and groups", "https://wiki.archlinux.org/title/Users_and_groups"),
    ],
    "useradd(8)": [
        ("Users and groups", "https://wiki.archlinux.org/title/Users_and_groups"),
    ],
    "userdel(8)": [
        ("Users and groups", "https://wiki.archlinux.org/title/Users_and_groups"),
    ],
    "passwd(5)": [
        ("Users and groups", "https://wiki.archlinux.org/title/Users_and_groups"),
    ],
    "group(5)": [
        ("Users and groups", "https://wiki.archlinux.org/title/Users_and_groups"),
    ],
    "nologin(8)": [
        ("Users and groups", "https://wiki.archlinux.org/title/Users_and_groups"),
    ],
    # Sudoers Privilege Manager
    "sudoers(5)": [
        ("Sudo", "https://wiki.archlinux.org/title/Sudo"),
    ],
    "visudo(8)": [
        ("Sudo", "https://wiki.archlinux.org/title/Sudo"),
    ],
    "sudo(8)": [
        ("Sudo", "https://wiki.archlinux.org/title/Sudo"),
    ],
    # Journal & Log Explorer
    "journalctl(1)": [
        ("systemd/Journal", "https://wiki.archlinux.org/title/Systemd/Journal"),
    ],
    "journald.conf(5)": [
        ("systemd/Journal", "https://wiki.archlinux.org/title/Systemd/Journal"),
    ],
    "systemd-journald.service(8)": [
        ("systemd/Journal", "https://wiki.archlinux.org/title/Systemd/Journal"),
    ],
    # Advanced File Permissions
    "acl(5)": [
        ("Access Control Lists", "https://wiki.archlinux.org/title/Access_Control_Lists"),
        ("File permissions and attributes", "https://wiki.archlinux.org/title/File_permissions_and_attributes"),
    ],
    "setfacl(1)": [
        ("Access Control Lists", "https://wiki.archlinux.org/title/Access_Control_Lists"),
    ],
    "getfacl(1)": [
        ("Access Control Lists", "https://wiki.archlinux.org/title/Access_Control_Lists"),
    ],
    "chattr(1)": [
        ("File permissions and attributes", "https://wiki.archlinux.org/title/File_permissions_and_attributes#File_attributes"),
    ],
    "lsattr(1)": [
        ("File permissions and attributes", "https://wiki.archlinux.org/title/File_permissions_and_attributes#File_attributes"),
    ],
    # Bootloader & Kernel Parameter Editor
    "kernel-command-line(7)": [
        ("Kernel parameters", "https://wiki.archlinux.org/title/Kernel_parameters"),
        ("Arch boot process", "https://wiki.archlinux.org/title/Arch_boot_process#Boot_loader"),
    ],
    "bootctl(1)": [
        ("systemd-boot", "https://wiki.archlinux.org/title/Systemd-boot"),
        ("Kernel parameters", "https://wiki.archlinux.org/title/Kernel_parameters"),
    ],
    "loader.conf(5)": [
        ("systemd-boot", "https://wiki.archlinux.org/title/Systemd-boot"),
    ],
    "grub-mkconfig(8)": [
        ("GRUB", "https://wiki.archlinux.org/title/GRUB"),
        ("Kernel parameters", "https://wiki.archlinux.org/title/Kernel_parameters"),
    ],
}


def get_arch_wiki_links(man_pages: list[str] | str, max_links: int = 2) -> list[tuple[str, str]]:
    """Return up to ``max_links`` deduplicated ``(title, url)`` Arch Wiki links for the given man pages."""
    refs = [man_pages] if isinstance(man_pages, str) else list(man_pages)
    seen_urls: set[str] = set()
    result: list[tuple[str, str]] = []

    for ref in refs:
        norm = normalize_man_ref(ref)
        page, _, _ = parse_man_ref(norm)
        candidates = MAN_TO_ARCH_WIKI.get(norm)
        if not candidates:
            for k, v in MAN_TO_ARCH_WIKI.items():
                if k.startswith(f"{page}("):
                    candidates = v
                    break
        if candidates:
            for title, url in candidates:
                if url not in seen_urls:
                    seen_urls.add(url)
                    result.append((title, url))
                    if len(result) >= max_links:
                        return result
    return result


def format_arch_wiki_links(links: list[tuple[str, str]], prefix_key: str = "banner_arch_wiki_prefix") -> str:
    """Format a list of ``(title, url)`` Arch Wiki tuples into clickable HTML."""
    if not links:
        return ""
    anchors = [
        f"<a href='{html.escape(url)}' style='color: #58a6ff; text-decoration: underline; font-weight: 600;'>"
        f"{html.escape(title)} ↗</a>"
        for title, url in links
    ]
    return (
        f"<span style='color: #9ea4b0; font-size: 12px;'>"
        f"<b>{tr(prefix_key)}</b> {' &nbsp;·&nbsp; '.join(anchors)}</span>"
    )


def parse_man_ref(ref: str) -> tuple[str, str, str]:
    """Parse a man reference like 'systemd.timer(5)' or 'man:fstab(5)' into (page, section, url)."""
    clean = ref.strip()
    if clean.startswith("man:"):
        clean = clean[4:].strip()
    m = re.match(r"^([A-Za-z0-9_.:+-]+)(?:\((\d+[a-zA-Z]*)\))?$", clean)
    if m:
        page = m.group(1)
        sec = m.group(2) or ""
    else:
        page = clean
        sec = ""
    url = f"https://man.archlinux.org/man/{page}.{sec}" if sec else f"https://man.archlinux.org/man/{page}"
    return page, sec, url


def normalize_man_ref(ref: str) -> str:
    """Return canonical 'page(section)' or 'page' string."""
    page, sec, _ = parse_man_ref(ref)
    return f"{page}({sec})" if sec else page


def get_man_guide(ref: str) -> tuple[str, str, str]:
    """Return (tab_label, section_badge, friendly_html_description) for a man page ref."""
    norm = normalize_man_ref(ref)
    page, sec, _ = parse_man_ref(norm)
    sec_badge = SECTION_DESCRIPTIONS.get(sec, f"Section {sec}" if sec else "Linux Manual Page")

    if norm in MAN_PAGE_GUIDES:
        tab_label, desc = MAN_PAGE_GUIDES[norm]
        return tab_label, sec_badge, desc

    # Fallback by page name without section
    for k, (tab_label, desc) in MAN_PAGE_GUIDES.items():
        if k.startswith(f"{page}("):
            return tab_label, sec_badge, desc

    default_desc = (
        f"<b>System Manual Page (<code>{norm}</code>):</b> Official Linux reference documentation "
        f"for <code>{page}</code>. Use the search bar below to jump to specific options or flags."
    )
    return norm, sec_badge, default_desc


def format_man_links(man_pages: list[str]) -> str:
    """Format a list of man page specs (e.g. ['fstab(5)', 'mount(8)']) as clickable HTML links."""
    if not man_pages:
        return ""
    links = []
    for ref in man_pages:
        label = normalize_man_ref(ref)
        links.append(
            f"<a href='man:{label}' style='color: #729fe6; text-decoration: underline; font-family: monospace;'>{label}</a>"
        )
    return f"<span style='color: #9498a1; font-size: 11px;'><b>{tr('banner_man_pages_prefix')}</b> {' &nbsp;·&nbsp; '.join(links)}</span>"


_ANSI_COLOR_MAP: dict[int, str] = {
    30: "#6e7681",
    31: "#ff7b72",
    32: "#7ee787",
    33: "#e3b341",
    34: "#79c0ff",
    35: "#d2a8ff",
    36: "#a5d6ff",
    37: "#e6edf3",
    90: "#8b949e",
    91: "#ffa198",
    92: "#aff5b4",
    93: "#f8e3a1",
    94: "#a5d6ff",
    95: "#e2c5ff",
    96: "#b3f0ff",
    97: "#ffffff",
}

_SGR_TOKEN_RE = re.compile(r"(\x1b\[[0-9;]*m)")
_XREF_RE = re.compile(r"\b([a-zA-Z0-9_.:+-]{2,})\(([1-8][a-zA-Z]*)\)")
_SPAN_XREF_RE = re.compile(
    r"(<span style=\"[^\"]*\">([a-zA-Z0-9_.:+-]{2,})</span>)\(([1-8][a-zA-Z]*)\)"
)


def ansi_man_to_terminal_html(raw: str) -> str:
    """Convert raw `man` output (with ANSI SGR escapes or backspace overstrikes) into
    clean, rich terminal HTML with zero control/escape characters (no square boxes).
    """
    if not raw:
        return ""

    # 1. Remove OSC-8 hyperlink sequences (\x1b]8;;...\x1b\\ or \x07) and non-SGR CSI sequences
    text = re.sub(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)", "", raw)
    text = re.sub(r"\x1b\[[0-9;?]*[A-Za-ln-z]", "", text)

    # 2. Convert classic roff backspace overstrikes if present:
    #    _\x08X -> underline X, X\x08X -> bold X
    if "\x08" in text:
        text = re.sub(r"_\x08([^\x08])", "\x1b[4m\\1\x1b[24m", text)
        text = re.sub(r"([^\x08])\x08\1", "\x1b[1m\\1\x1b[22m", text)
        while "\x08" in text:
            text = re.sub(r".\x08", "", text)

    # 3. Parse SGR sequences (\x1b[...m) into styled HTML spans
    tokens = _SGR_TOKEN_RE.split(text)
    bold = False
    underline = False
    fg_color: str | None = None

    out_parts: list[str] = []

    def _format_chunk(chunk_str: str) -> str:
        # Strip any remaining stray control chars (except \n and \t) so square glyphs never appear
        clean_chunk = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", chunk_str)
        if not clean_chunk:
            return ""
        escaped = html.escape(clean_chunk)
        # Make man page cross-references like mount(8) clickable links
        escaped = _XREF_RE.sub(
            r"<a href='man:\1(\2)' style='color: #58a6ff; text-decoration: underline;'>\1(\2)</a>",
            escaped,
        )
        styles: list[str] = []
        if bold and underline:
            styles.append("color: #79c0ff; font-weight: bold; text-decoration: underline;")
        elif bold:
            styles.append(f"color: {fg_color or '#79c0ff'}; font-weight: bold;")
        elif underline:
            styles.append(f"color: {fg_color or '#e3b341'}; text-decoration: underline;")
        elif fg_color:
            styles.append(f"color: {fg_color};")

        if styles:
            return f"<span style=\"{' '.join(styles)}\">{escaped}</span>"
        return escaped

    for tok in tokens:
        if not tok:
            continue
        if tok.startswith("\x1b[") and tok.endswith("m"):
            code_str = tok[2:-1]
            codes = [int(c) if c.isdigit() else 0 for c in code_str.split(";")] if code_str else [0]
            for c in codes:
                if c == 0:
                    bold = False
                    underline = False
                    fg_color = None
                elif c == 1:
                    bold = True
                elif c == 4:
                    underline = True
                elif c == 22:
                    bold = False
                elif c == 24:
                    underline = False
                elif c in _ANSI_COLOR_MAP:
                    fg_color = _ANSI_COLOR_MAP[c]
                elif c == 39:
                    fg_color = None
        else:
            out_parts.append(_format_chunk(tok))

    body = "".join(out_parts)
    body = _SPAN_XREF_RE.sub(
        r"<a href='man:\2(\3)' style='color: #58a6ff; text-decoration: underline;'>\1(\3)</a>",
        body,
    )
    return (
        "<pre style=\"font-family: 'JetBrains Mono', 'Fira Code', monospace; "
        "font-size: 12px; line-height: 1.45; color: #d8dee9; margin: 0; white-space: pre-wrap;\">"
        f"{body}</pre>"
    )


def load_man_page_raw(page: str, section: str = "") -> str:
    """Load raw formatted manual page output from local `man` command with SGR formatting."""
    if not shutil.which("man"):
        return ""
    cmd = ["man", "-P", "cat"]
    if section:
        cmd.append(section)
    cmd.append(page)
    env = {k: v for k, v in os.environ.items() if not k.startswith("MAN")}
    env["MANWIDTH"] = "105"
    env["MAN_KEEP_FORMATTING"] = "1"
    env["LC_ALL"] = "C.UTF-8"
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env, timeout=5)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout
        # Retry without section if section wasn't installed locally
        if section:
            res2 = subprocess.run(["man", "-P", "cat", page], capture_output=True, text=True, check=False, env=env, timeout=5)
            if res2.returncode == 0 and res2.stdout.strip():
                return res2.stdout
    except Exception:
        pass
    return ""


def launch_man_in_system_terminal(page: str, section: str = "") -> bool:
    """Attempt to launch the user's native system terminal emulator running `man [section] page`."""
    man_args = ["man", section, page] if section else ["man", page]
    terminals = [
        ("x-terminal-emulator", ["-e", *man_args]),
        ("ptyxis", ["--", *man_args]),
        ("kgx", ["--", *man_args]),
        ("gnome-terminal", ["--", *man_args]),
        ("konsole", ["-e", *man_args]),
        ("xfce4-terminal", ["-x", *man_args]),
        ("kitty", man_args),
        ("alacritty", ["-e", *man_args]),
        ("wezterm", ["start", "--", *man_args]),
        ("foot", man_args),
        ("tilix", ["-e", *man_args]),
        ("mate-terminal", ["-x", *man_args]),
        ("lxterminal", ["-e", *man_args]),
        ("xterm", ["-e", *man_args]),
    ]
    for binary, args in terminals:
        if shutil.which(binary):
            try:
                subprocess.Popen([binary, *args], start_new_session=True)
                return True
            except Exception:
                continue
    return False


class ManPageTabWidget(QWidget):
    """Single tab inside ManPageHelpWindow displaying a beginner-friendly guide card
    and an embedded terminal man page viewer.
    """

    manLinkClicked = pyqtSignal(str)

    def __init__(self, man_ref: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.man_ref = normalize_man_ref(man_ref)
        self.page, self.section, self.online_url = parse_man_ref(self.man_ref)
        self.tab_label, self.sec_badge, self.friendly_desc = get_man_guide(self.man_ref)
        self.man_cmd_str = f"{self.section} {self.page}" if self.section else self.page

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 1. Beginner-friendly explanation card
        guide_card = QFrame()
        guide_card.setObjectName("manGuideCard")
        guide_card.setStyleSheet(
            """
            QFrame#manGuideCard {
                background-color: #1a1d24;
                border: 1px solid #282d38;
                border-left: 3px solid #3fb950;
                border-radius: 6px;
                padding: 8px 10px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
            """
        )
        g_layout = QVBoxLayout(guide_card)
        g_layout.setContentsMargins(6, 4, 6, 4)
        g_layout.setSpacing(4)

        badge_row = QHBoxLayout()
        lbl_sec = QLabel(f"  {self.sec_badge}  ")
        lbl_sec.setStyleSheet(
            "background-color: #1a2636; color: #79c0ff; font-weight: bold; font-size: 11px; "
            "border-radius: 4px; padding: 2px 6px;"
        )
        badge_row.addWidget(lbl_sec)
        badge_row.addStretch()

        tab_wiki_links = get_arch_wiki_links(self.man_ref, max_links=2)
        if tab_wiki_links:
            lbl_tab_wiki = QLabel(format_arch_wiki_links(tab_wiki_links, prefix_key="banner_arch_wiki_prefix"))
            lbl_tab_wiki.setTextFormat(Qt.TextFormat.RichText)
            lbl_tab_wiki.setOpenExternalLinks(True)
            badge_row.addWidget(lbl_tab_wiki)

        g_layout.addLayout(badge_row)

        lbl_desc = QLabel(self.friendly_desc)
        lbl_desc.setWordWrap(True)
        lbl_desc.setTextFormat(Qt.TextFormat.RichText)
        lbl_desc.setStyleSheet("color: #f0f3f6; font-size: 12px; line-height: 1.4;")
        g_layout.addWidget(lbl_desc)

        layout.addWidget(guide_card)

        # 2. Embedded Terminal Header & Search Bar
        term_bar = QFrame()
        term_bar.setObjectName("manTerminalBar")
        term_bar.setStyleSheet(
            """
            QFrame#manTerminalBar {
                background-color: #161920;
                border: 1px solid #282d38;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 4px 8px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
            """
        )
        tb_layout = QHBoxLayout(term_bar)
        tb_layout.setContentsMargins(6, 4, 6, 4)
        tb_layout.setSpacing(8)

        lbl_prompt = QLabel(f"<span style='color: #7ee787; font-weight: bold;'>$</span> <code>man {self.man_cmd_str}</code>")
        lbl_prompt.setStyleSheet("font-family: monospace; font-size: 12px; color: #e6edf3;")
        tb_layout.addWidget(lbl_prompt)

        tb_layout.addSpacing(8)
        tb_layout.addWidget(QLabel(tr("man_search_label")))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText(tr("man_search_placeholder"))
        self.txt_search.setClearButtonEnabled(True)
        self.txt_search.returnPressed.connect(self._find_next)
        tb_layout.addWidget(self.txt_search, stretch=1)

        btn_next = QPushButton(tr("man_btn_next"))
        btn_next.setFixedHeight(24)
        btn_next.clicked.connect(self._find_next)
        tb_layout.addWidget(btn_next)

        btn_prev = QPushButton(tr("man_btn_prev"))
        btn_prev.setFixedHeight(24)
        btn_prev.clicked.connect(self._find_prev)
        tb_layout.addWidget(btn_prev)

        btn_term = QPushButton(tr("man_btn_open_terminal"))
        btn_term.setFixedHeight(24)
        btn_term.setToolTip(tr("man_btn_open_terminal_tooltip", cmd=self.man_cmd_str))
        btn_term.clicked.connect(lambda: launch_man_in_system_terminal(self.page, self.section))
        tb_layout.addWidget(btn_term)

        btn_online = QPushButton(tr("man_btn_open_online"))
        btn_online.setFixedHeight(24)
        btn_online.setToolTip(self.online_url)
        btn_online.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.online_url)))
        tb_layout.addWidget(btn_online)

        layout.addWidget(term_bar)

        # 3. Embedded Terminal Output View
        self.viewer = QTextBrowser()
        self.viewer.setReadOnly(True)
        self.viewer.setOpenLinks(False)
        self.viewer.anchorClicked.connect(self._on_anchor_clicked)
        mono_font = QFont("JetBrains Mono", 10)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        self.viewer.setFont(mono_font)
        self.viewer.setStyleSheet(
            """
            QTextBrowser {
                background-color: #0f1115;
                color: #d8dee9;
                border: 1px solid #282d38;
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
                padding: 10px 12px;
                selection-background-color: #203554;
                selection-color: #ffffff;
            }
            """
        )

        raw_man = load_man_page_raw(self.page, self.section)
        if raw_man:
            self.viewer.setHtml(ansi_man_to_terminal_html(raw_man))
        else:
            fallback = html.escape(tr("man_not_installed", ref=self.man_ref, url=self.online_url))
            self.viewer.setHtml(f"<pre style='color: #e3b341; font-family: monospace;'>{fallback}</pre>")

        layout.addWidget(self.viewer, stretch=1)

    def _on_anchor_clicked(self, url: QUrl) -> None:
        scheme = url.scheme()
        raw = url.toString()
        if scheme == "man" or raw.startswith("man:"):
            self.manLinkClicked.emit(raw)
        elif scheme in ("http", "https"):
            QDesktopServices.openUrl(url)

    def _find_next(self) -> None:
        query = self.txt_search.text().strip()
        if not query:
            return
        if not self.viewer.find(query):
            cursor = self.viewer.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            self.viewer.setTextCursor(cursor)
            self.viewer.find(query)

    def _find_prev(self) -> None:
        query = self.txt_search.text().strip()
        if not query:
            return
        if not self.viewer.find(query, QTextDocument.FindFlag.FindBackward):
            cursor = self.viewer.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.viewer.setTextCursor(cursor)
            self.viewer.find(query, QTextDocument.FindFlag.FindBackward)


class ManPageHelpWindow(QDialog):
    """Tabbed Help & Manual Page Viewer window displaying all relevant man pages
    for an application as tabs, with beginner explanations and embedded terminal rendering.
    """

    def __init__(
        self,
        man_pages: list[str] | str,
        initial_page: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle(tr("man_window_title"))
        self.resize(1020, 720)
        self.setMinimumSize(760, 520)

        if isinstance(man_pages, str):
            pages_list = [man_pages]
            if initial_page is None:
                initial_page = man_pages
        else:
            pages_list = list(man_pages)

        self._tab_index_by_ref: dict[str, int] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Top beginner-friendly intro banner explaining what man pages & section numbers mean
        intro_frame = QFrame()
        intro_frame.setObjectName("manIntroFrame")
        intro_frame.setStyleSheet(
            """
            QFrame#manIntroFrame {
                background-color: #1c2128;
                border: 1px solid #30363d;
                border-left: 3px solid #6899e6;
                border-radius: 4px;
                padding: 6px 10px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
            """
        )
        intro_layout = QVBoxLayout(intro_frame)
        intro_layout.setContentsMargins(4, 2, 4, 2)
        intro_layout.setSpacing(4)
        lbl_intro = QLabel(tr("man_intro_banner"))
        lbl_intro.setWordWrap(True)
        lbl_intro.setTextFormat(Qt.TextFormat.RichText)
        lbl_intro.setStyleSheet("color: #c9d1d9; font-size: 11px; line-height: 1.35;")
        intro_layout.addWidget(lbl_intro)

        self.arch_wiki_links = get_arch_wiki_links(pages_list, max_links=2)
        self.lbl_arch_wiki = QLabel(format_arch_wiki_links(self.arch_wiki_links, prefix_key="man_arch_wiki_prefix"))
        self.lbl_arch_wiki.setWordWrap(True)
        self.lbl_arch_wiki.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_arch_wiki.setOpenExternalLinks(True)
        intro_layout.addWidget(self.lbl_arch_wiki)
        self.lbl_arch_wiki.setVisible(bool(self.arch_wiki_links))

        layout.addWidget(intro_frame)

        # Tab widget for each man page
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        layout.addWidget(self.tabs, stretch=1)

        for ref in pages_list:
            self.add_man_page_tab(ref)

        if initial_page:
            self.select_or_add_man_page(initial_page)

        # Bottom close bar
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()
        btn_close = QPushButton(tr("man_btn_close"))
        btn_close.clicked.connect(self.close)
        bottom_bar.addWidget(btn_close)
        layout.addLayout(bottom_bar)

    def add_man_page_tab(self, man_ref: str) -> int:
        norm = normalize_man_ref(man_ref)
        if norm in self._tab_index_by_ref:
            return self._tab_index_by_ref[norm]

        tab_widget = ManPageTabWidget(norm, parent=self)
        tab_widget.manLinkClicked.connect(self.select_or_add_man_page)
        idx = self.tabs.addTab(tab_widget, tab_widget.tab_label)
        self._tab_index_by_ref[norm] = idx
        return idx

    def select_or_add_man_page(self, man_ref: str) -> None:
        norm = normalize_man_ref(man_ref)
        page_only, _, _ = parse_man_ref(norm)

        # Check exact match first
        if norm in self._tab_index_by_ref:
            self.tabs.setCurrentIndex(self._tab_index_by_ref[norm])
            return

        # Check match by page name if section wasn't specified
        for existing_ref, idx in self._tab_index_by_ref.items():
            ex_page, _, _ = parse_man_ref(existing_ref)
            if ex_page == page_only:
                self.tabs.setCurrentIndex(idx)
                return

        idx = self.add_man_page_tab(norm)
        self.tabs.setCurrentIndex(idx)

    @property
    def viewer(self) -> QTextBrowser:
        """Return the active tab's QTextBrowser for backwards compatibility."""
        cur = self.tabs.currentWidget()
        if isinstance(cur, ManPageTabWidget):
            return cur.viewer
        return QTextBrowser(self)


# Alias for backwards compatibility
ManPageDialog = ManPageHelpWindow


def open_man_page(
    man_ref: str | None = None,
    parent: QWidget | None = None,
    man_pages: list[str] | None = None,
) -> ManPageHelpWindow:
    """Open or focus the tabbed ManPageHelpWindow for the active window and select ``man_ref``."""
    if parent is None:
        app = QApplication.instance()
        if isinstance(app, QApplication):
            parent = app.activeWindow()

    host_win = parent.window() if isinstance(parent, QWidget) else None

    # Discover configured man_pages from the host window's LivePreviewBanner if not passed
    if not man_pages and host_win is not None:
        banner = getattr(host_win, "preview_banner", None)
        if banner is not None and getattr(banner, "man_pages", None):
            man_pages = list(banner.man_pages)

    if not man_pages and man_ref:
        man_pages = [normalize_man_ref(man_ref)]
    elif not man_pages:
        man_pages = ["systemctl(1)"]

    # Reuse existing help window attached to host_win if available
    existing_win: ManPageHelpWindow | None = getattr(host_win, "_man_help_window", None) if host_win else None
    if existing_win is not None:
        for mp in man_pages:
            existing_win.add_man_page_tab(mp)
        if man_ref:
            existing_win.select_or_add_man_page(man_ref)
        existing_win.show()
        existing_win.raise_()
        existing_win.activateWindow()
        return existing_win

    win = ManPageHelpWindow(man_pages=man_pages, initial_page=man_ref, parent=host_win)
    if host_win is not None:
        setattr(host_win, "_man_help_window", win)
    win.show()
    win.raise_()
    win.activateWindow()
    return win


class LivePreviewBanner(QFrame):
    """A top-of-window banner that dynamically updates in real time to show the exact
    entry or command being generated as the user toggles options, with a Help button
    opening the tabbed Manual Page viewer.
    """

    diffRequested = pyqtSignal()

    def __init__(
        self,
        title: str | None = None,
        subtitle: str | None = None,
        man_pages: list[str] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        if title is None:
            title = tr("banner_default_title")
        if subtitle is None:
            subtitle = tr("banner_default_subtitle")
        self.man_pages: list[str] = list(man_pages) if man_pages else []

        self.setObjectName("livePreviewBanner")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            """
            #livePreviewBanner {
                background-color: #1a1d24;
                border: 1px solid #282d38;
                border-left: 3px solid #388bfd;
                border-radius: 6px;
                padding: 6px;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(4)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        self.title_label = QLabel(f"{title}")
        self.title_label.setStyleSheet("font-weight: 600; color: #85abf2; font-size: 13px; letter-spacing: 0.2px;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        # Help & Man Pages button (opens tabbed ManPageHelpWindow)
        self.btn_help = QPushButton(tr("banner_btn_help"), self)
        self.btn_help.setToolTip(tr("banner_btn_help_tooltip"))
        self.btn_help.setFixedHeight(26)
        self.btn_help.setStyleSheet(
            "QPushButton { background-color: #1a2942; color: #8ab4f8; border: 1px solid #2a416a; "
            "border-radius: 5px; font-size: 12px; font-weight: 600; padding: 3px 10px; } "
            "QPushButton:hover { background-color: #233758; color: #ffffff; }"
        )
        self.btn_help.clicked.connect(self.open_help_window)
        header_layout.addWidget(self.btn_help)
        self.btn_help.setVisible(bool(self.man_pages))

        self.btn_copy = QPushButton(tr("banner_btn_copy"))
        self.btn_copy.setToolTip(tr("banner_btn_copy_tooltip"))
        self.btn_copy.setFixedHeight(26)
        self.btn_copy.setStyleSheet("font-size: 12px; padding: 3px 10px;")
        self.btn_copy.clicked.connect(self._copy_to_clipboard)
        header_layout.addWidget(self.btn_copy)

        self.btn_diff = QPushButton(tr("banner_btn_diff"))
        self.btn_diff.setToolTip(tr("banner_btn_diff_tooltip"))
        self.btn_diff.setFixedHeight(26)
        self.btn_diff.setStyleSheet("font-size: 12px; padding: 3px 10px;")
        self.btn_diff.clicked.connect(self.diffRequested.emit)
        header_layout.addWidget(self.btn_diff)

        layout.addLayout(header_layout)

        # Monospace live code box
        self.code_display = QTextEdit()
        self.code_display.setReadOnly(True)
        self.code_display.setFixedHeight(40)
        self.code_display.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.code_display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        mono_font = QFont("JetBrains Mono", 10)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        self.code_display.setFont(mono_font)
        self.code_display.setStyleSheet(
            """
            QTextEdit {
                background-color: #111317;
                color: #3fb950;
                border: 1px solid #252a35;
                border-radius: 5px;
                padding: 5px 8px;
                font-size: 13px;
                font-weight: 500;
            }
            """
        )
        layout.addWidget(self.code_display)

        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(12)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet("color: #9198a1; font-size: 12px;")
        footer_layout.addWidget(self.subtitle_label, 1)

        self.arch_wiki_links = get_arch_wiki_links(self.man_pages, max_links=2)
        self.arch_wiki_label = QLabel(format_arch_wiki_links(self.arch_wiki_links), self)
        self.arch_wiki_label.setTextFormat(Qt.TextFormat.RichText)
        self.arch_wiki_label.setOpenExternalLinks(True)
        footer_layout.addWidget(self.arch_wiki_label)
        self.arch_wiki_label.setVisible(bool(self.arch_wiki_links))

        layout.addLayout(footer_layout)

    def set_text(self, text: str) -> None:
        """Update the live text display."""
        self.code_display.setPlainText(text.strip())

    def get_text(self) -> str:
        """Return the current displayed text."""
        return self.code_display.toPlainText()

    def set_title(self, title: str) -> None:
        self.title_label.setText(f"{title}")

    def set_subtitle(self, subtitle: str) -> None:
        """Update the subtitle explanation."""
        self.subtitle_label.setText(subtitle)

    def set_man_pages(self, man_pages: list[str]) -> None:
        """Configure the manual pages opened by the Help button."""
        self.man_pages = list(man_pages) if man_pages else []
        self.btn_help.setVisible(bool(self.man_pages))
        self.arch_wiki_links = get_arch_wiki_links(self.man_pages, max_links=2)
        self.arch_wiki_label.setText(format_arch_wiki_links(self.arch_wiki_links))
        self.arch_wiki_label.setVisible(bool(self.arch_wiki_links))

    def open_help_window(self, initial_page: str | None = None) -> ManPageHelpWindow:
        """Open the tabbed ManPageHelpWindow for this banner's man pages."""
        first_page = initial_page if isinstance(initial_page, str) and initial_page else (
            self.man_pages[0] if self.man_pages else None
        )
        return open_man_page(man_ref=first_page, parent=self.window(), man_pages=self.man_pages)

    def _copy_to_clipboard(self) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(self.get_text())
            original_text = self.btn_copy.text()
            self.btn_copy.setText(tr("banner_btn_copied"))
            self.btn_copy.setStyleSheet("background-color: #2da44e; color: #ffffff; font-weight: bold; font-size: 11px;")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: self._reset_copy_btn(original_text))

    def _reset_copy_btn(self, original_text: str) -> None:
        self.btn_copy.setText(original_text)
        self.btn_copy.setStyleSheet("font-size: 11px; padding: 2px 8px;")
