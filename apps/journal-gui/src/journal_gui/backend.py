"""Backend wrappers and queries for journalctl logs and vacuum maintenance."""

import shutil
import subprocess
from linux_gui_core.runner.executor import ExecutionResult, SafeExecutor


class JournalBackend:
    @staticmethod
    def list_boot_sessions() -> list[tuple[str, str]]:
        """Returns list of (boot_id_or_offset, display_label) from 'journalctl --list-boots'."""
        boots = [("0", "Current Boot (0)"), ("-1", "Previous Boot (-1)")]
        if not shutil.which("journalctl"):
            return boots

        try:
            res = subprocess.run(
                ["journalctl", "--list-boots", "--no-pager"],
                capture_output=True,
                text=True,
                check=False,
            )
            parsed = []
            for line in res.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    offset = parts[0]
                    # Format: 0 4b95f... Sun 2026-10-11 14:00:00 BST—Sun 2026-10-11 17:00:00 BST
                    date_part = " ".join(parts[2:6]) if len(parts) >= 6 else offset
                    parsed.append((offset, f"Boot {offset} ({date_part})"))
            if parsed:
                return parsed
        except Exception:
            pass
        return boots

    @staticmethod
    def get_disk_usage() -> str:
        """Returns disk space occupied by journal files."""
        if not shutil.which("journalctl"):
            return "journalctl not available"
        res = subprocess.run(["journalctl", "--disk-usage"], capture_output=True, text=True, check=False)
        return res.stdout.strip() or res.stderr.strip()

    @staticmethod
    def build_query_cmd(
        boot: str = "0",
        unit: str = "",
        priority: str = "warning",
        grep: str = "",
        lines: int = 200,
        user_mode: bool = False,
    ) -> list[str]:
        cmd = ["journalctl"]
        if user_mode:
            cmd.append("--user")
        if boot != "all":
            cmd.extend(["-b", boot])
        if unit.strip():
            cmd.extend(["-u", unit.strip()])
        if priority != "all":
            cmd.extend(["-p", priority])
        if grep.strip():
            cmd.extend(["-g", grep.strip()])
        if lines > 0:
            cmd.extend(["-n", str(lines)])
        cmd.append("--no-pager")
        return cmd

    @staticmethod
    def fetch_logs(
        boot: str = "0",
        unit: str = "",
        priority: str = "warning",
        grep: str = "",
        lines: int = 200,
        user_mode: bool = False,
    ) -> tuple[str, str]:
        cmd = JournalBackend.build_query_cmd(boot, unit, priority, grep, lines, user_mode)
        cmd_str = " ".join(cmd)
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            output = res.stdout if res.returncode == 0 else (res.stderr or res.stdout)
            return cmd_str, output or "(No logs found matching specified criteria)"
        except Exception as e:
            return cmd_str, f"Error running journalctl: {e}"

    @staticmethod
    def execute_vacuum(vacuum_arg: str) -> ExecutionResult:
        """Runs journalctl --vacuum-time=... or --vacuum-size=... with root escalation."""
        cmd = ["journalctl", vacuum_arg]
        return SafeExecutor.run_command(cmd, elevated=True)
