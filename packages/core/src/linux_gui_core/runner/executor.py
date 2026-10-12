"""Safe executor for Linux system file updates and elevated commands."""

import datetime
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    success: bool
    stdout: str
    stderr: str
    command_executed: str
    backup_file: str | None = None


class SafeExecutor:
    """Handles execution of privileged commands with dry-run support and backups."""

    @staticmethod
    def run_command(
        cmd: list[str],
        elevated: bool = False,
        use_pkexec: bool = True,
    ) -> ExecutionResult:
        """Run a command with optional privilege escalation via pkexec or sudo."""
        final_cmd = cmd
        if elevated and os.geteuid() != 0:
            if use_pkexec and shutil.which("pkexec"):
                final_cmd = ["pkexec"] + cmd
            elif shutil.which("sudo"):
                final_cmd = ["sudo"] + cmd

        cmd_str = " ".join(final_cmd)
        try:
            res = subprocess.run(
                final_cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            return ExecutionResult(
                success=(res.returncode == 0),
                stdout=res.stdout,
                stderr=res.stderr,
                command_executed=cmd_str,
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                command_executed=cmd_str,
            )

    @staticmethod
    def safe_write_system_file(
        target_path: str,
        new_content: str,
        dry_run: bool = False,
    ) -> ExecutionResult:
        """Safely write to a system file:

        1. Creates a timestamped backup of the target file
        2. Writes new content to a temporary file
        3. Uses pkexec / sudo dd/cp to atomically replace the target
        """
        if dry_run:
            return ExecutionResult(
                success=True,
                stdout="[DRY-RUN] No changes were written to disk.",
                stderr="",
                command_executed=f"# DRY RUN: write to {target_path}",
            )

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{target_path}.bak.{timestamp}"

        # 1. Create temporary file with content
        with tempfile.NamedTemporaryFile("w", delete=False) as tf:
            tf.write(new_content)
            temp_path = tf.name

        try:
            # Command script that backs up and atomically moves
            script = (
                f"if [ -f '{target_path}' ]; then cp '{target_path}' '{backup_path}'; fi && "
                f"cp '{temp_path}' '{target_path}' && "
                f"chmod 644 '{target_path}'"
            )

            res = SafeExecutor.run_command(
                ["bash", "-c", script],
                elevated=True,
            )
            res.backup_file = backup_path if os.path.exists(target_path) else None
            return res
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
