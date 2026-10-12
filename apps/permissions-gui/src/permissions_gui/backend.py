"""Backend wrappers for POSIX ACLs (getfacl/setfacl) and Linux file attributes (lsattr/chattr)."""

from dataclasses import dataclass
import os
import shutil
import subprocess
from linux_gui_core.runner.executor import ExecutionResult, SafeExecutor


@dataclass
class ACLEntry:
    is_default: bool
    principal_type: str  # user, group, other, mask
    principal_name: str  # e.g. alice, developers
    permissions: str     # rwx, rw-, r--


class PermissionsBackend:
    @staticmethod
    def get_basic_stat(path: str) -> dict:
        """Fetch file owner, group, and octal mode."""
        if not os.path.exists(path):
            return {}
        try:
            st = os.stat(path)
            import pwd, grp
            owner = pwd.getpwuid(st.st_uid).pw_name
            group = grp.getgrgid(st.st_gid).gr_name
            mode_oct = oct(st.st_mode)[-3:]
            return {
                "owner": owner,
                "group": group,
                "mode": mode_oct,
                "is_dir": os.path.isdir(path),
            }
        except Exception:
            return {}

    @staticmethod
    def parse_acls(path: str) -> list[ACLEntry]:
        """Runs getfacl and parses extended ACL entries."""
        if not shutil.which("getfacl") or not os.path.exists(path):
            return []
        try:
            res = subprocess.run(["getfacl", "-cp", path], capture_output=True, text=True, check=False)
            entries = []
            for line in res.stdout.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                is_def = line.startswith("default:")
                clean = line[8:] if is_def else line
                parts = clean.split(":")
                if len(parts) >= 3:
                    p_type = parts[0]   # user, group, mask, other
                    p_name = parts[1]   # e.g. alice
                    perms = parts[2]    # e.g. rwx
                    entries.append(
                        ACLEntry(
                            is_default=is_def,
                            principal_type=p_type,
                            principal_name=p_name or "(base)",
                            permissions=perms,
                        )
                    )
            return entries
        except Exception:
            return []

    @staticmethod
    def build_setfacl_cmd(
        path: str,
        principal_type: str,
        name: str,
        perms: str,
        is_default: bool = False,
        recursive: bool = False,
    ) -> list[str]:
        cmd = ["setfacl"]
        if recursive:
            cmd.append("-R")
        tag = "d:" if is_default else ""
        spec = f"{tag}{principal_type}:{name}:{perms}"
        cmd.extend(["-m", spec, path])
        return cmd

    @staticmethod
    def apply_setfacl(
        path: str,
        principal_type: str,
        name: str,
        perms: str,
        is_default: bool = False,
        recursive: bool = False,
    ) -> ExecutionResult:
        cmd = PermissionsBackend.build_setfacl_cmd(path, principal_type, name, perms, is_default, recursive)
        return SafeExecutor.run_command(cmd, elevated=True)

    @staticmethod
    def remove_acl_entry(path: str, entry: ACLEntry) -> ExecutionResult:
        tag = "d:" if entry.is_default else ""
        name = "" if entry.principal_name == "(base)" else entry.principal_name
        spec = f"{tag}{entry.principal_type}:{name}"
        cmd = ["setfacl", "-x", spec, path]
        return SafeExecutor.run_command(cmd, elevated=True)

    @staticmethod
    def remove_all_acls(path: str) -> ExecutionResult:
        cmd = ["setfacl", "-b", path]
        return SafeExecutor.run_command(cmd, elevated=True)

    @staticmethod
    def get_file_attributes(path: str) -> str:
        """Returns raw lsattr flag string (e.g. '----i--------------e--')."""
        if not shutil.which("lsattr") or not os.path.exists(path):
            return ""
        try:
            res = subprocess.run(["lsattr", "-d", path], capture_output=True, text=True, check=False)
            if res.returncode == 0:
                parts = res.stdout.split()
                if parts:
                    return parts[0]
        except Exception:
            pass
        return ""

    @staticmethod
    def apply_chattr(path: str, flag_str: str) -> ExecutionResult:
        """Runs chattr +/-flag path."""
        cmd = ["chattr", flag_str, path]
        return SafeExecutor.run_command(cmd, elevated=True)
