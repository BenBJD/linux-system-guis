"""Backend queries and operations for Linux sysctl kernel parameters."""

from dataclasses import dataclass
import glob
import os
import subprocess
from linux_gui_core.runner.executor import ExecutionResult, SafeExecutor


@dataclass
class SysctlPreset:
    """Objective, man-page-backed metadata for a common Linux kernel tunable."""

    key: str
    category: str
    kernel_default: str
    typical_range: str
    title: str
    description: str
    man_page: str = "proc_sys(5)"
    value_options: tuple[tuple[str, str], ...] = ()
    security_note: str = ""


SYSCTL_PRESETS: list[SysctlPreset] = [
    # -------------------------------------------------------------------------
    # Memory & Writeback — proc_sys_vm(5)
    # -------------------------------------------------------------------------
    SysctlPreset(
        key="vm.swappiness",
        category="Memory & Writeback",
        kernel_default="60",
        typical_range="0 to 200 (kernel default: 60)",
        title="Swappiness (Anon vs. Page Cache Reclaim Balance)",
        description=(
            "Defines the rough relative I/O cost of swapping anonymous memory versus reclaiming filesystem page cache "
            "(proc_sys_vm(5)). At 100, the kernel assumes equal I/O cost and applies memory pressure equally to anonymous "
            "pages and page cache. The upstream Linux kernel default is 60. Lower values (e.g. 10) instruct the kernel to "
            "prefer reclaiming filesystem page cache over swapping application memory; values above 100 (up to 200) may be "
            "used when swap resides on fast in-RAM compressed devices (such as zram) that are faster than filesystem storage."
        ),
        man_page="proc_sys_vm(5)",
        value_options=(
            ("60", "60 — Upstream kernel default (balanced reclaim)"),
            ("10", "10 — Strongly prefer reclaiming page cache over swapping anon memory"),
            ("1", "1 — Minimum swapping without disabling swap completely"),
            ("0", "0 — Avoid swapping anonymous memory unless free + file-backed pages < high watermark"),
            ("100", "100 — Equal I/O cost between anonymous memory and filesystem page cache"),
            ("180", "180 — Prefer swapping anonymous pages (often used with fast in-RAM zram swap)"),
        ),
    ),
    SysctlPreset(
        key="vm.vfs_cache_pressure",
        category="Memory & Writeback",
        kernel_default="100",
        typical_range="0 to 1000 (kernel default: 100)",
        title="Directory & Inode Cache Reclamation Pressure",
        description=(
            "Controls the tendency of the kernel to reclaim memory used for caching VFS directory and inode objects "
            "(dentries and inodes) relative to pagecache and swap (proc_sys_vm(5)). At the kernel default of 100, the kernel "
            "attempts to reclaim dentries and inodes at a 'fair' rate with respect to pagecache and swapcache reclaim. "
            "Decreasing below 100 (e.g. 50) causes the kernel to prefer retaining directory and inode caches; increasing "
            "beyond 100 causes the kernel to prefer reclaiming dentries and inodes."
        ),
        man_page="proc_sys_vm(5)",
        value_options=(
            ("100", "100 — Upstream kernel default (fair reclaim rate relative to pagecache)"),
            ("50", "50 — Prefer retaining directory and inode (VFS) caches longer in RAM"),
            ("200", "200 — Reclaim directory and inode caches more aggressively"),
        ),
    ),
    SysctlPreset(
        key="vm.dirty_ratio",
        category="Memory & Writeback",
        kernel_default="20",
        typical_range="1 to 100 % of available memory (kernel default: 20)",
        title="Synchronous Writeback Dirty Threshold (%)",
        description=(
            "Contains, as a percentage of total available memory that contains free pages and reclaimable pages, the "
            "number of pages at which a process which is generating disk writes will itself start writing out dirty data "
            "synchronously (proc_sys_vm(5)). Lower values reduce maximum unwritten data buffered in RAM and prevent large "
            "I/O stalls when flushing to slow storage media."
        ),
        man_page="proc_sys_vm(5)",
        value_options=(
            ("20", "20 — Upstream kernel default (20% of available memory)"),
            ("10", "10 — Earlier synchronous writeback (10% of available memory)"),
            ("40", "40 — Allow larger write buffering in RAM (40% of available memory)"),
        ),
    ),
    SysctlPreset(
        key="vm.dirty_background_ratio",
        category="Memory & Writeback",
        kernel_default="10",
        typical_range="1 to 100 % of available memory (kernel default: 10)",
        title="Background Writeback Flusher Threshold (%)",
        description=(
            "Contains, as a percentage of total available memory that contains free pages and reclaimable pages, the "
            "number of pages at which the background kernel flusher threads will start writing out dirty data "
            "asynchronously to disk (proc_sys_vm(5)). Should remain lower than vm.dirty_ratio."
        ),
        man_page="proc_sys_vm(5)",
        value_options=(
            ("10", "10 — Upstream kernel default (10% of available memory)"),
            ("5", "5 — Start background writeback flusher threads earlier (5%)"),
            ("3", "3 — Frequent small background flushes (3%)"),
        ),
    ),
    SysctlPreset(
        key="vm.max_map_count",
        category="Memory & Writeback",
        kernel_default="65530",
        typical_range=">= 65530 (upstream kernel default: 65530; systemd/Arch default: 1048576)",
        title="Maximum Memory Map Areas per Process (VMA Limit)",
        description=(
            "Defines the maximum number of memory map areas (VMAs) a process may have (proc_sys_vm(5)). While the upstream "
            "kernel default is 65530, memory-intensive applications, databases (Elasticsearch), and Windows games running "
            "under Wine/Proton frequently allocate hundreds of thousands of mappings; modern systemd distributions often "
            "raise this to 1048576 or 2147483642."
        ),
        man_page="proc_sys_vm(5)",
        value_options=(
            ("65530", "65530 — Upstream Linux kernel default"),
            ("262144", "262144 — 256K memory map areas (required by Elasticsearch)"),
            ("1048576", "1048576 — 1M memory map areas (standard systemd / gaming workload limit)"),
            ("2147483642", "2147483642 — Maximum 32-bit signed limit (SteamOS / heavy Proton workloads)"),
        ),
    ),
    SysctlPreset(
        key="vm.overcommit_memory",
        category="Memory & Writeback",
        kernel_default="0",
        typical_range="0 (heuristic default), 1 (always overcommit), 2 (strict commit limit)",
        title="Virtual Memory Overcommit Accounting Mode",
        description=(
            "Controls the kernel's virtual memory overcommit accounting policy (proc_sys_vm(5)): 0 = heuristic overcommit "
            "(kernel default: obvious overcommits are refused while reasonable overcommits succeed); 1 = always overcommit "
            "(useful for scientific workloads using sparse arrays or Redis background fork saves); 2 = strict accounting "
            "(never commit more address space than swap + vm.overcommit_ratio % of physical RAM)."
        ),
        man_page="proc_sys_vm(5)",
        value_options=(
            ("0", "0 — Heuristic overcommit (upstream kernel default)"),
            ("1", "1 — Always allow overcommit (used by Redis / sparse array workloads)"),
            ("2", "2 — Strict accounting (never exceed swap + overcommit_ratio of RAM)"),
        ),
    ),
    # -------------------------------------------------------------------------
    # Networking & TCP/IP — tcp(7), ip(7), icmp(7), proc_sys_net(5)
    # -------------------------------------------------------------------------
    SysctlPreset(
        key="net.ipv4.ip_forward",
        category="Networking & TCP/IP",
        kernel_default="0",
        typical_range="0 (disabled, kernel default) or 1 (enabled)",
        title="IPv4 Packet Forwarding Between Interfaces",
        description=(
            "Controls forwarding of IPv4 packets between network interfaces on the system (ip(7)). The upstream kernel "
            "default is 0 (host mode: packets are not routed between interfaces). Setting this to 1 enables router mode, "
            "which is required for VPN gateways (WireGuard/OpenVPN), NAT routers, and container/VM network bridges "
            "(Docker/Podman/libvirt). Note: enabling IPv4 forwarding also resets interface routing parameters to router defaults."
        ),
        man_page="ip(7)",
        value_options=(
            ("0", "0 — Disabled (upstream kernel default; standard host mode)"),
            ("1", "1 — Enabled (router mode; required for VPN gateways, NAT, and container bridges)"),
        ),
    ),
    SysctlPreset(
        key="net.ipv6.conf.all.disable_ipv6",
        category="Networking & TCP/IP",
        kernel_default="0",
        typical_range="0 (IPv6 enabled, kernel default) or 1 (IPv6 disabled)",
        title="Disable IPv6 Operation on All Interfaces",
        description=(
            "Controls whether IPv6 operation is disabled across all network interfaces (proc_sys_net(5)). At the kernel "
            "default of 0, IPv6 is enabled. Setting to 1 disables the IPv6 stack on all current interfaces."
        ),
        man_page="proc_sys_net(5)",
        value_options=(
            ("0", "0 — IPv6 enabled on all interfaces (upstream kernel default)"),
            ("1", "1 — Disable IPv6 operation on all interfaces"),
        ),
    ),
    SysctlPreset(
        key="net.core.default_qdisc",
        category="Networking & TCP/IP",
        kernel_default="fq_codel",
        typical_range="fq_codel, fq, cake, pfifo_fast",
        title="Default Network Packet Queuing Discipline (qdisc)",
        description=(
            "Specifies the default packet scheduling / queuing discipline (qdisc) attached to network interfaces "
            "(proc_sys_net(5)). 'fq_codel' (Fair Queuing Controlled Delay) is the standard default on Arch Linux and systemd "
            "distributions to mitigate bufferbloat; 'fq' (Fair Queue traffic policing) provides per-flow pacing required "
            "by TCP BBR; 'cake' provides integrated AQM if sch_cake is loaded; 'pfifo_fast' is the legacy FIFO queue."
        ),
        man_page="proc_sys_net(5)",
        value_options=(
            ("fq_codel", "fq_codel — Fair Queuing Controlled Delay (standard systemd/Arch default)"),
            ("fq", "fq — Fair Queue scheduler with per-flow pacing (pairs with TCP BBR)"),
            ("cake", "cake — Common Applications Kept Enhanced AQM (requires sch_cake module)"),
            ("pfifo_fast", "pfifo_fast — Legacy 3-band FIFO queue"),
        ),
    ),
    SysctlPreset(
        key="net.ipv4.tcp_congestion_control",
        category="Networking & TCP/IP",
        kernel_default="cubic",
        typical_range="cubic (kernel default), bbr, reno",
        title="TCP Congestion Control Algorithm",
        description=(
            "Sets the congestion control algorithm used for new TCP connections (tcp(7)). 'cubic' is the upstream Linux "
            "kernel default optimized for high-bandwidth networks. 'bbr' (Bottleneck Bandwidth and Round-trip propagation "
            "time, requires the tcp_bbr module) models bottleneck bandwidth and RTT rather than relying solely on packet loss."
        ),
        man_page="tcp(7)",
        value_options=(
            ("cubic", "cubic — CUBIC congestion control (upstream Linux kernel default)"),
            ("bbr", "bbr — Bottleneck Bandwidth and RTT (requires tcp_bbr kernel module)"),
            ("reno", "reno — Classic TCP NewReno congestion control"),
        ),
    ),
    SysctlPreset(
        key="net.ipv4.tcp_fastopen",
        category="Networking & TCP/IP",
        kernel_default="1",
        typical_range="Bitmask: 0 (off), 1 (client default), 2 (server), 3 (client + server)",
        title="TCP Fast Open (TFO) Bitmask (RFC 7413)",
        description=(
            "Enables TCP Fast Open (RFC 7413) to exchange data during the initial TCP SYN handshake (tcp(7)). The value is "
            "a bitmask: 0 disables TFO; 1 (upstream kernel default) enables TFO for client connections (sending data in SYN); "
            "2 enables TFO for listening server sockets; 3 (1+2) enables TFO for both client and server connections."
        ),
        man_page="tcp(7)",
        value_options=(
            ("1", "1 — Enable TCP Fast Open for outgoing client connections (kernel default)"),
            ("3", "3 — Enable TCP Fast Open for both client and listening server sockets (1 + 2)"),
            ("0", "0 — Disable TCP Fast Open completely"),
        ),
    ),
    SysctlPreset(
        key="net.ipv4.tcp_syncookies",
        category="Networking & TCP/IP",
        kernel_default="1",
        typical_range="0 (disabled), 1 (enabled when SYN backlog fills, default), 2 (always)",
        title="TCP SYN Cookies (SYN Flood Protection)",
        description=(
            "Controls cryptographic TCP SYN cookie generation to protect listening sockets when the SYN backlog queue "
            "overflows during a SYN flood attack (tcp(7)). At the kernel default of 1, SYN cookies are sent only when the "
            "socket's max_syn_backlog is exceeded."
        ),
        man_page="tcp(7)",
        value_options=(
            ("1", "1 — Send SYN cookies when SYN backlog overflows (upstream kernel default)"),
            ("0", "0 — Disable TCP SYN cookies"),
            ("2", "2 — Always send SYN cookies unconditionally (for testing)"),
        ),
        security_note="Keeping tcp_syncookies set to 1 protects listening TCP services from SYN flood denial-of-service exhaustion.",
    ),
    SysctlPreset(
        key="net.ipv4.conf.all.rp_filter",
        category="Networking & TCP/IP",
        kernel_default="2",
        typical_range="0 (no source validation), 1 (strict RFC 3704), 2 (loose mode, systemd default)",
        title="Reverse Path Filtering (IP Spoofing Protection)",
        description=(
            "Controls source address verification (Reverse Path Filtering, RFC 3704) for incoming IPv4 packets (ip(7)). "
            "0 disables source validation; 1 (Strict Mode) drops packets if the return path does not match the exact ingress "
            "interface; 2 (Loose Mode, configured by systemd 50-default.conf) drops packets only if the source address is "
            "not reachable via any interface (compatible with asymmetric routing and multi-homed hosts)."
        ),
        man_page="ip(7)",
        value_options=(
            ("2", "2 — Loose mode source validation (systemd default; works with multi-homed/VPN setups)"),
            ("1", "1 — Strict RFC 3704 Reverse Path Filtering (drop if ingress != best return interface)"),
            ("0", "0 — No source validation"),
        ),
        security_note="Enabling Reverse Path Filtering (1 or 2) mitigates IP source-address spoofing on local networks.",
    ),
    SysctlPreset(
        key="net.ipv4.conf.all.accept_redirects",
        category="Networking & TCP/IP",
        kernel_default="0",
        typical_range="0 (ignore ICMP redirects) or 1 (accept ICMP redirects)",
        title="Accept ICMP Redirect Messages (IPv4)",
        description=(
            "Controls whether the kernel accepts ICMP redirect messages that modify the host's routing table (ip(7)). "
            "The kernel defaults to 0 when IP forwarding is enabled (router mode) and 1 in host mode, though network "
            "hardening guides commonly set this to 0 to prevent malicious routing table manipulation."
        ),
        man_page="ip(7)",
        value_options=(
            ("0", "0 — Ignore ICMP redirect messages (prevents routing table tampering)"),
            ("1", "1 — Accept ICMP redirect messages (default in pure host mode)"),
        ),
        security_note="Setting accept_redirects = 0 prevents MITM attackers on the local link from altering host routes via forged ICMP redirects.",
    ),
    SysctlPreset(
        key="net.ipv4.icmp_echo_ignore_all",
        category="Networking & TCP/IP",
        kernel_default="0",
        typical_range="0 (respond to ICMP echo/ping, default) or 1 (ignore all ICMP echo requests)",
        title="Ignore All Incoming IPv4 ICMP Echo (Ping) Requests",
        description=(
            "Controls whether the kernel ignores all incoming ICMP ECHO_REQUEST (ping) packets (icmp(7)). At the kernel "
            "default of 0, the system responds normally to pings; when set to 1, the kernel silently drops all IPv4 ping requests."
        ),
        man_page="icmp(7)",
        value_options=(
            ("0", "0 — Respond normally to ICMP echo/ping requests (upstream kernel default)"),
            ("1", "1 — Silently ignore all incoming IPv4 ICMP echo requests"),
        ),
    ),
    SysctlPreset(
        key="net.core.somaxconn",
        category="Networking & TCP/IP",
        kernel_default="4096",
        typical_range=">= 128 (upstream kernel default since Linux 5.4: 4096)",
        title="Maximum Socket Listen Backlog (somaxconn)",
        description=(
            "Defines the upper limit on the queue length of completely established sockets waiting to be accepted via "
            "listen(2) (proc_sys_net(5)). Since Linux 5.4, the upstream kernel default is 4096. High-concurrency web "
            "servers or reverse proxies may increase this value."
        ),
        man_page="proc_sys_net(5)",
        value_options=(
            ("4096", "4096 — Upstream Linux kernel default (since Linux 5.4)"),
            ("8192", "8192 — Increased listen queue for busy web/proxy servers"),
            ("65535", "65535 — High-throughput server listen backlog"),
        ),
    ),
    # -------------------------------------------------------------------------
    # File System & Limits — inotify(7), proc_sys_fs(5)
    # -------------------------------------------------------------------------
    SysctlPreset(
        key="fs.inotify.max_user_watches",
        category="File System & Limits",
        kernel_default="524288",
        typical_range="8192 to 1048576 (per-UID watch limit)",
        title="Maximum inotify File Watches per User",
        description=(
            "Specifies an upper limit on the number of inotify watches that can be created per real user ID (inotify(7)). "
            "Modern kernels scale the default dynamically with RAM (up to 524288 or 1048576), while older kernels defaulted "
            "to 8192. IDEs (PyCharm, VS Code), file indexers, and sync clients watching large source trees require a high limit."
        ),
        man_page="inotify(7)",
        value_options=(
            ("524288", "524288 — Standard modern limit (512K watches per user)"),
            ("1048576", "1048576 — High limit for large monorepos and file sync clients (1M watches)"),
            ("65536", "65536 — Moderate limit (64K watches per user)"),
        ),
    ),
    SysctlPreset(
        key="fs.inotify.max_user_instances",
        category="File System & Limits",
        kernel_default="128",
        typical_range="128 to 8192 (kernel default: 128; systemd often sets 1024)",
        title="Maximum inotify Instances per User",
        description=(
            "Specifies an upper limit on the number of inotify instances (file descriptors returned by inotify_init(2)) "
            "that can be created per real user ID (inotify(7)). When running many desktop applications, containers, or "
            "file watchers simultaneously, hitting the upstream default of 128 causes 'Too many open files' errors."
        ),
        man_page="inotify(7)",
        value_options=(
            ("128", "128 — Upstream Linux kernel default"),
            ("1024", "1024 — Expanded per-user instance limit for desktop/container workloads"),
            ("2048", "2048 — High instance limit for heavy multi-container workstations"),
        ),
    ),
    SysctlPreset(
        key="fs.protected_hardlinks",
        category="File System & Limits",
        kernel_default="1",
        typical_range="0 (unrestricted) or 1 (restricted, systemd default)",
        title="Protected Hardlinks Creation Restriction",
        description=(
            "When set to 1 (proc_sys_fs(5)), hardlinks cannot be created by users to files they do not own or do not have "
            "read/write access to. Prevents privilege-escalation vulnerabilities caused by hardlinking setuid binaries or "
            "sensitive files into world-writable directories."
        ),
        man_page="proc_sys_fs(5)",
        value_options=(
            ("1", "1 — Restrict hardlink creation to owned/accessible files (standard hardened default)"),
            ("0", "0 — Legacy unrestricted hardlink behavior"),
        ),
        security_note="Keeping fs.protected_hardlinks = 1 prevents local privilege-escalation attacks via hardlinks to setuid files.",
    ),
    SysctlPreset(
        key="fs.protected_symlinks",
        category="File System & Limits",
        kernel_default="1",
        typical_range="0 (unrestricted) or 1 (restricted, systemd default)",
        title="Protected Symlinks in Sticky World-Writable Directories",
        description=(
            "When set to 1 (proc_sys_fs(5)), symbolic links inside sticky world-writable directories (such as /tmp) are "
            "followed only when the symlink owner matches either the directory owner or the follower's UID. Prevents "
            "classic /tmp symlink race condition attacks."
        ),
        man_page="proc_sys_fs(5)",
        value_options=(
            ("1", "1 — Restrict following untrusted symlinks in sticky directories (standard hardened default)"),
            ("0", "0 — Legacy unrestricted symlink following"),
        ),
        security_note="Keeping fs.protected_symlinks = 1 prevents TOCTOU symlink race attacks in /tmp and /var/tmp.",
    ),
    # -------------------------------------------------------------------------
    # Kernel & Security — proc_sys_kernel(5)
    # -------------------------------------------------------------------------
    SysctlPreset(
        key="kernel.sysrq",
        category="Kernel & Security",
        kernel_default="16",
        typical_range="0 (disabled), 1 (all functions), or bitmask (e.g. 16, 176, 244)",
        title="Magic SysRq Key Bitmask",
        description=(
            "Bitmask controlling emergency recovery functions allowed via the Alt+SysRq keyboard combo (proc_sys_kernel(5)): "
            "0 disables SysRq completely; 1 enables every function; values > 1 are a bitmask of permitted operations "
            "(2 = console loglevel, 4 = keyboard/SAK, 8 = debugging dumps, 16 = sync mounted filesystems, "
            "32 = remount read-only, 64 = process signalling/kill/oom, 128 = reboot/poweroff; 176 = 16+32+128)."
        ),
        man_page="proc_sys_kernel(5)",
        value_options=(
            ("16", "16 — Only allow emergency filesystem sync (common distribution default)"),
            ("176", "176 — Allow sync (16) + remount-ro (32) + reboot/poweroff (128)"),
            ("244", "244 — Allow keyboard/SAK (4) + sync (16) + remount-ro (32) + kill (64) + reboot (128)"),
            ("1", "1 — Enable all Magic SysRq recovery and debugging functions"),
            ("0", "0 — Disable Magic SysRq key completely"),
        ),
    ),
    SysctlPreset(
        key="kernel.dmesg_restrict",
        category="Kernel & Security",
        kernel_default="1",
        typical_range="0 (unrestricted) or 1 (restricted to CAP_SYSLOG)",
        title="Restrict Kernel Log Buffer (dmesg) Access",
        description=(
            "Controls whether unprivileged users are prevented from using dmesg(1) or syslog(2) to read messages from the "
            "kernel log buffer (proc_sys_kernel(5)). When set to 1, reading the kernel ring buffer requires CAP_SYSLOG "
            "(root or systemd-journal group)."
        ),
        man_page="proc_sys_kernel(5)",
        value_options=(
            ("1", "1 — Restrict dmesg access to privileged users with CAP_SYSLOG"),
            ("0", "0 — Allow any unprivileged local user to run dmesg without sudo"),
        ),
        security_note="Setting kernel.dmesg_restrict = 1 prevents unprivileged local processes from harvesting kernel memory addresses or diagnostic info from dmesg.",
    ),
    SysctlPreset(
        key="kernel.kptr_restrict",
        category="Kernel & Security",
        kernel_default="1",
        typical_range="0 (exposed), 1 (hidden from unprivileged, default), 2 (hidden from all)",
        title="Kernel Pointer Address Exposure Restriction",
        description=(
            "Controls whether kernel pointer addresses exposed via /proc and other interfaces are replaced with zeros "
            "(proc_sys_kernel(5)). 0 = pointers are not hidden; 1 (default) = pointers printed with %pK are zeroed unless "
            "the reader has CAP_SYSLOG; 2 = kernel pointers are zeroed for all users regardless of privilege."
        ),
        man_page="proc_sys_kernel(5)",
        value_options=(
            ("1", "1 — Hide kernel pointers from unprivileged users lacking CAP_SYSLOG (default)"),
            ("2", "2 — Always hide kernel pointers even from root/CAP_SYSLOG"),
            ("0", "0 — Expose raw kernel pointers (only for kernel debugging)"),
        ),
        security_note="Hiding kernel pointer addresses (1 or 2) strengthens KASLR against local kernel exploit payloads.",
    ),
    SysctlPreset(
        key="kernel.yama.ptrace_scope",
        category="Kernel & Security",
        kernel_default="1",
        typical_range="0 (classic), 1 (restricted child-only, default), 2 (admin-only), 3 (no attach)",
        title="Yama ptrace Process Debugging Scope",
        description=(
            "Controls which processes may attach a debugger (ptrace(2), gdb, strace) to another running process "
            "(proc_sys_kernel(5)): 0 = classic permissions (any process with matching UID can ptrace another); "
            "1 (default) = restricted ptrace (only a parent process or one explicitly allowed via prctl(PR_SET_PTRACER) "
            "can debug a descendant); 2 = admin-only attach (requires CAP_SYS_PTRACE); 3 = no process may ptrace at all."
        ),
        man_page="proc_sys_kernel(5)",
        value_options=(
            ("1", "1 — Restricted ptrace: only direct parent processes or CAP_SYS_PTRACE (default)"),
            ("0", "0 — Classic ptrace: allow attaching gdb/strace to any process with the same UID"),
            ("2", "2 — Admin-only ptrace: require CAP_SYS_PTRACE (sudo) to attach debuggers"),
            ("3", "3 — Disable ptrace completely (cannot be lowered without reboot)"),
        ),
        security_note="Setting ptrace_scope >= 1 prevents a compromised user process from reading credentials out of other running user processes (e.g. ssh-agent or browser).",
    ),
    SysctlPreset(
        key="kernel.unprivileged_bpf_disabled",
        category="Kernel & Security",
        kernel_default="2",
        typical_range="0 (allowed), 1 (disabled permanently until reboot), 2 (disabled, toggleable by root)",
        title="Restrict Unprivileged eBPF Syscall Access",
        description=(
            "Controls whether unprivileged users (without CAP_BPF or CAP_SYS_ADMIN) may invoke the bpf(2) system call "
            "(proc_sys_kernel(5)): 0 = unprivileged eBPF allowed; 1 = unprivileged eBPF disabled and cannot be re-enabled "
            "without a reboot; 2 (upstream default) = unprivileged eBPF disabled, but root can toggle it back to 0."
        ),
        man_page="proc_sys_kernel(5)",
        value_options=(
            ("2", "2 — Disable unprivileged bpf(2) calls, allow root to toggle (upstream default)"),
            ("1", "1 — Permanently disable unprivileged bpf(2) calls until next reboot"),
            ("0", "0 — Allow unprivileged processes to load eBPF programs"),
        ),
        security_note="Disabling unprivileged eBPF (1 or 2) eliminates a major class of local kernel privilege-escalation and Spectre-style side-channel attacks.",
    ),
    SysctlPreset(
        key="kernel.nmi_watchdog",
        category="Kernel & Security",
        kernel_default="1",
        typical_range="0 (disabled — saves power/CPU counter) or 1 (enabled)",
        title="Hard Lockup Detector (NMI Watchdog)",
        description=(
            "Enables or disables the Non-Maskable Interrupt (NMI) hardware watchdog that detects hard CPU lockups "
            "(proc_sys_kernel(5)). Disabling the NMI watchdog (0) frees one hardware performance counter and slightly "
            "reduces idle power consumption on laptops (commonly recommended on the Arch Wiki Sysctl page)."
        ),
        man_page="proc_sys_kernel(5)",
        value_options=(
            ("1", "1 — Enable NMI hard-lockup watchdog (upstream kernel default)"),
            ("0", "0 — Disable NMI watchdog (saves power and frees a CPU performance counter)"),
        ),
    ),
]


PRESET_BY_KEY: dict[str, SysctlPreset] = {p.key: p for p in SYSCTL_PRESETS}


class SysctlBackend:
    """Backend queries and privileged execution helpers for sysctl."""

    @staticmethod
    def infer_man_page_for_key(key: str) -> str:
        """Returns the most specific man page documenting a sysctl key."""
        preset = PRESET_BY_KEY.get(key)
        if preset:
            return preset.man_page
        if key.startswith("vm."):
            return "proc_sys_vm(5)"
        if key.startswith("net.ipv4.tcp_"):
            return "tcp(7)"
        if key.startswith("net.ipv4.icmp_"):
            return "icmp(7)"
        if key.startswith("net.ipv4."):
            return "ip(7)"
        if key.startswith("net."):
            return "proc_sys_net(5)"
        if key.startswith("fs.inotify."):
            return "inotify(7)"
        if key.startswith("fs."):
            return "proc_sys_fs(5)"
        if key.startswith("kernel."):
            return "proc_sys_kernel(5)"
        return "proc_sys(5)"

    @staticmethod
    def list_config_files(conf_dir: str = "/etc/sysctl.d") -> list[str]:
        """Lists persistent sysctl drop-in files in /etc/sysctl.d/ plus default 99-sysctl.conf."""
        default_file = os.path.join(conf_dir, "99-sysctl.conf")
        custom_file = os.path.join(conf_dir, "99-custom.conf")
        files: list[str] = []
        if os.path.isdir(conf_dir):
            found = sorted(glob.glob(os.path.join(conf_dir, "*.conf")))
            files.extend(found)
        for candidate in (default_file, custom_file):
            if candidate not in files:
                files.append(candidate)
        return files

    @staticmethod
    def read_config_file(target_file: str) -> str:
        """Reads an existing sysctl configuration file if present."""
        if not os.path.exists(target_file):
            return ""
        try:
            with open(target_file, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except OSError:
            res = SafeExecutor.run_command(["cat", target_file], elevated=True)
            return res.stdout if res.success else ""

    @staticmethod
    def build_updated_config_content(key: str, value: str, existing_content: str) -> str:
        """Returns the updated content of a sysctl.d configuration file with key = value."""
        lines: list[str] = []
        found = False
        for line in existing_content.splitlines():
            stripped = line.strip()
            if not stripped.startswith("#") and not stripped.startswith(";"):
                if stripped.startswith(f"{key} =") or stripped.startswith(f"{key}="):
                    lines.append(f"{key} = {value}")
                    found = True
                    continue
            lines.append(line)
        if not found:
            if not lines:
                lines.append("# Custom kernel parameters managed by sysctl-gui (see sysctl.d(5))")
            lines.append(f"{key} = {value}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def get_live_value(key: str) -> str:
        """Reads the current kernel live value for a parameter from /proc/sys (or sysctl -n fallback)."""
        proc_path = os.path.join("/proc/sys", *key.split("."))
        if os.path.isfile(proc_path):
            try:
                with open(proc_path, "r", encoding="utf-8", errors="replace") as f:
                    return f.read().strip()
            except OSError:
                pass
        try:
            res = subprocess.run(
                ["sysctl", "-n", key],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                return res.stdout.strip()
        except Exception:
            pass
        return "(unavailable)"

    @staticmethod
    def list_all_parameters() -> list[tuple[str, str]]:
        """Queries sysctl -a to return (key, value) pairs."""
        params = []
        try:
            res = subprocess.run(["sysctl", "-a"], capture_output=True, text=True, check=False)
            for line in res.stdout.splitlines():
                if " = " in line:
                    k, v = line.split(" = ", 1)
                    params.append((k.strip(), v.strip()))
        except Exception:
            pass
        return params

    @staticmethod
    def apply_live_value(key: str, value: str) -> ExecutionResult:
        """Runs sudo sysctl -w key=value (temporary until reboot)."""
        cmd = ["sysctl", "-w", f"{key}={value}"]
        return SafeExecutor.run_command(cmd, elevated=True)

    @staticmethod
    def reload_all_configs() -> ExecutionResult:
        """Runs sudo sysctl --system to reload all sysctl.d drop-in configuration files."""
        return SafeExecutor.run_command(["sysctl", "--system"], elevated=True)

    @staticmethod
    def save_persistent_config(
        key: str,
        value: str,
        target_file: str = "/etc/sysctl.d/99-sysctl.conf",
    ) -> ExecutionResult:
        """Appends or updates the key in /etc/sysctl.d/ and runs sysctl --system."""
        existing_content = SysctlBackend.read_config_file(target_file)
        new_content = SysctlBackend.build_updated_config_content(key, value, existing_content)
        write_res = SafeExecutor.safe_write_system_file(target_file, new_content)
        if not write_res.success:
            return write_res

        # Reload kernel with sysctl --system
        return SafeExecutor.run_command(["sysctl", "--system"], elevated=True)
