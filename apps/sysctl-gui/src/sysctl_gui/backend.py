"""Backend queries and operations for Linux sysctl kernel parameters."""

from dataclasses import dataclass
import glob
import os
import shutil
import subprocess
from linux_gui_core.runner.executor import ExecutionResult, SafeExecutor


@dataclass
class SysctlPreset:
    key: str
    category: str
    recommended_value: str
    typical_range: str
    title: str
    description: str
    safety_rating: str


SYSCTL_PRESETS: list[SysctlPreset] = [
    # Memory & Swapping
    SysctlPreset(
        key="vm.swappiness",
        category="Memory & Caching",
        recommended_value="10",
        typical_range="0 to 200 (default: 10)",
        title="Swappiness Aggressiveness",
        description="Controls how aggressively the Linux kernel moves memory pages to swap disk. Lower values (e.g. 10) prioritize keeping applications in fast physical RAM and reduce SSD wear on desktop PCs.",
        safety_rating="Safe",
    ),
    SysctlPreset(
        key="vm.vfs_cache_pressure",
        category="Memory & Caching",
        recommended_value="50",
        typical_range="0 to 1000 (default: 50)",
        title="Directory & Inode Cache Retention",
        description="Controls kernel tendency to reclaim directory/file metadata caches. Setting to 50 keeps directory structures cached in RAM longer, speeding up file managers and terminal navigations.",
        safety_rating="Safe",
    ),
    SysctlPreset(
        key="vm.dirty_ratio",
        category="Memory & Caching",
        recommended_value="20",
        typical_range="1 to 100 (default: 20)",
        title="Dirty Memory Max Threshold (%)",
        description="Percentage of total system memory that can hold unwritten 'dirty' data before active processes are forced to write data to disk.",
        safety_rating="Safe",
    ),
    SysctlPreset(
        key="vm.dirty_background_ratio",
        category="Memory & Caching",
        recommended_value="10",
        typical_range="1 to 100 (default: 10)",
        title="Background Flusher Wakeup (%)",
        description="Percentage of memory holding dirty data where the pdflush background kernel thread wakes up to begin writing pages to storage.",
        safety_rating="Safe",
    ),
    # Networking
    SysctlPreset(
        key="net.ipv4.ip_forward",
        category="Networking",
        recommended_value="1",
        typical_range="0 (disabled) or 1 (enabled)",
        title="IPv4 Packet Forwarding (Router/VPN)",
        description="Enables kernel packet routing between network interfaces. Required if running VPN gateways (WireGuard/OpenVPN), Docker container bridging, or Kubernetes.",
        safety_rating="Safe / Required for VPNs & Docker",
    ),
    SysctlPreset(
        key="net.ipv6.conf.all.disable_ipv6",
        category="Networking",
        recommended_value="0",
        typical_range="0 (enabled) or 1 (disabled)",
        title="Disable IPv6 Stack Globally",
        description="Completely turns off IPv6 packet processing across all network adapters. Useful if your local ISP has broken IPv6 routes causing DNS delays.",
        safety_rating="Safe / Troubleshooting",
    ),
    SysctlPreset(
        key="net.core.default_qdisc",
        category="Networking",
        recommended_value="cake",
        typical_range="fq, fq_codel, cake, pfifo_fast",
        title="Queueing Discipline (Bufferbloat Fix)",
        description="Algorithm managing network packet queues. Modern disciplines like 'cake' or 'fq_codel' virtually eliminate latency spikes and bufferbloat under heavy downloads.",
        safety_rating="Recommended Performance Boost",
    ),
    SysctlPreset(
        key="net.ipv4.tcp_congestion_control",
        category="Networking",
        recommended_value="bbr",
        typical_range="cubic, bbr, reno",
        title="TCP Congestion Control Algorithm",
        description="Google BBR algorithm measures bottleneck bandwidth and round-trip time, yielding significantly higher speeds over lossy Wi-Fi or long-distance internet connections.",
        safety_rating="Recommended Performance Boost",
    ),
    # System & Security
    SysctlPreset(
        key="fs.inotify.max_user_watches",
        category="File System & Tools",
        recommended_value="524288",
        typical_range="8192 to 1048576 (default: 8192/65536)",
        title="Maximum File Watchers (Inotify)",
        description="Upper limit on file system change listeners. Modern IDEs (VSCode, PyCharm) and tools like Dropbox easily exhaust the default limit on large projects.",
        safety_rating="Safe / Essential for Developers",
    ),
    SysctlPreset(
        key="kernel.sysrq",
        category="Recovery & Security",
        recommended_value="1",
        typical_range="0 (disabled) to 1 (all enabled) or 16/176",
        title="Magic SysRq Key Combinations",
        description="Enables emergency kernel hotkeys (Alt+SysRq+REISUB) to safely sync disks, terminate hung tasks, and reboot a completely frozen machine without data loss.",
        safety_rating="Recommended Recovery Tool",
    ),
    SysctlPreset(
        key="kernel.dmesg_restrict",
        category="Recovery & Security",
        recommended_value="1",
        typical_range="0 (open to all) or 1 (root only)",
        title="Kernel dmesg Access Restriction",
        description="Restricts viewing the kernel log buffer to users with CAP_SYSLOG or root. Prevents local unprivileged attackers from inspecting kernel memory pointers.",
        safety_rating="Security Hardening",
    ),
]


class SysctlBackend:
    @staticmethod
    def get_live_value(key: str) -> str:
        """Reads the current kernel live value for a parameter."""
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
    def save_persistent_config(
        key: str,
        value: str,
        target_file: str = "/etc/sysctl.d/99-custom.conf",
    ) -> ExecutionResult:
        """Appends or updates the key in /etc/sysctl.d/ and runs sysctl --system."""
        entry_line = f"{key} = {value}\n"
        existing_content = ""
        if os.path.exists(target_file):
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    existing_content = f.read()
            except Exception:
                res = SafeExecutor.run_command(["cat", target_file], elevated=True)
                existing_content = res.stdout

        lines = []
        found = False
        for line in existing_content.splitlines():
            if line.strip().startswith(f"{key} =") or line.strip().startswith(f"{key}="):
                lines.append(f"{key} = {value}")
                found = True
            else:
                lines.append(line)
        if not found:
            lines.append(f"{key} = {value}")

        new_content = "\n".join(lines) + "\n"
        write_res = SafeExecutor.safe_write_system_file(target_file, new_content)
        if not write_res.success:
            return write_res

        # Reload kernel with sysctl --system
        return SafeExecutor.run_command(["sysctl", "--system"], elevated=True)
