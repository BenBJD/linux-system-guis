"""Parser and visudo syntax validator for /etc/sudoers and /etc/sudoers.d/ files."""

from dataclasses import dataclass
import glob
import os
import re
import shutil
import subprocess
import tempfile


@dataclass
class SudoersRule:
    raw_line: str = ""
    is_comment: bool = False
    is_group: bool = False       # True if entity starts with %
    entity: str = "%wheel"       # username or group name (without % in entity field)
    hosts: str = "ALL"           # host list, default ALL
    runas_user: str = "ALL"      # user spec
    runas_group: str = "ALL"     # group spec
    nopasswd: bool = False       # NOPASSWD tag
    commands: str = "ALL"        # command list, default ALL

    def formatted_entity(self) -> str:
        clean = self.entity.lstrip("%")
        return f"%{clean}" if self.is_group else clean

    def to_line(self) -> str:
        if self.is_comment or self.raw_line.strip().startswith("#"):
            return self.raw_line

        entity_str = self.formatted_entity()
        runas = f"({self.runas_user}:{self.runas_group})" if self.runas_group else f"({self.runas_user})"
        tag = "NOPASSWD: " if self.nopasswd else ""
        return f"{entity_str} {self.hosts}={runas} {tag}{self.commands}"


class SudoersParser:
    RULE_REGEX = re.compile(
        r'^\s*(%?[A-Za-z0-9_.-]+)\s+([A-Za-z0-9_.*-]+)\s*=\s*\(([^):]+)(?::([^)]+))?\)\s*(?:(NOPASSWD|PASSWD):\s*)?(.*)$'
    )

    @classmethod
    def parse_line(cls, line: str) -> SudoersRule:
        clean = line.strip()
        if not clean or clean.startswith("#") or clean.startswith("Defaults"):
            return SudoersRule(raw_line=line.rstrip("\n"), is_comment=True)

        m = cls.RULE_REGEX.match(clean)
        if m:
            raw_entity, hosts, run_u, run_g, tag, cmds = m.groups()
            is_grp = raw_entity.startswith("%")
            ent = raw_entity.lstrip("%")
            nopasswd = (tag == "NOPASSWD") if tag else False
            return SudoersRule(
                raw_line=line.rstrip("\n"),
                is_comment=False,
                is_group=is_grp,
                entity=ent,
                hosts=hosts or "ALL",
                runas_user=run_u or "ALL",
                runas_group=run_g or "",
                nopasswd=nopasswd,
                commands=cmds.strip() or "ALL",
            )

        # Fallback for simple user ALL=(ALL) ALL
        parts = clean.split(maxsplit=2)
        if len(parts) >= 3 and "=" in parts[1]:
            ent = parts[0].lstrip("%")
            is_grp = parts[0].startswith("%")
            return SudoersRule(
                raw_line=line.rstrip("\n"),
                is_comment=False,
                is_group=is_grp,
                entity=ent,
                hosts="ALL",
                runas_user="ALL",
                runas_group="",
                nopasswd="NOPASSWD:" in clean,
                commands=parts[2].replace("NOPASSWD:", "").strip(),
            )

        return SudoersRule(raw_line=line.rstrip("\n"), is_comment=True)

    @staticmethod
    def is_valid_dropin_filename(name: str) -> tuple[bool, str]:
        """Validate drop-in filename according to sudoers specifications:

        - Must not contain '.' (sudo ignores files with periods)
        - Must not end with '~' (sudo ignores backup files)
        - Must only contain alphanumeric characters, hyphens, and underscores
        """
        if not name:
            return False, "Filename cannot be empty."
        if "." in name:
            return False, "Sudoers explicitly ignores files containing periods ('.'). Please remove any file extension."
        if name.endswith("~"):
            return False, "Sudoers explicitly ignores files ending with '~' (backup files)."
        if not re.match(r"^[A-Za-z0-9_-]+$", name):
            return False, "Filename should only contain alphanumeric characters, hyphens, and underscores (e.g. '10-admin', '99-wheel')."
        return True, ""

    @staticmethod
    def list_sudoers_files(dir_path: str = "/etc/sudoers.d") -> list[str]:
        """List sudoers files accessible without elevation."""
        files = ["/etc/sudoers"]
        if os.path.exists(dir_path):
            try:
                for f in sorted(glob.glob(os.path.join(dir_path, "*"))):
                    base = os.path.basename(f)
                    if not base.startswith(".") and not base.endswith("~") and "." not in base:
                        files.append(f)
            except Exception:
                pass
        return files

    @staticmethod
    def list_sudoers_files_elevated(dir_path: str = "/etc/sudoers.d") -> list[str]:
        """List all drop-in files in dir_path using elevated find/ls."""
        from linux_gui_core.runner.executor import SafeExecutor
        cmd = f"find '{dir_path}' -maxdepth 1 -type f"
        res = SafeExecutor.run_command(["bash", "-c", cmd], elevated=True)
        files = ["/etc/sudoers"]
        if res.success:
            for line in sorted(res.stdout.splitlines()):
                line = line.strip()
                if not line:
                    continue
                base = os.path.basename(line)
                if not base.startswith(".") and not base.endswith("~") and "." not in base:
                    if line not in files:
                        files.append(line)
        return files

    @staticmethod
    def validate_with_visudo(content: str) -> tuple[bool, str]:
        """Validates sudoers content using 'visudo -c -f <tempfile>'.

        Prevents syntax errors and root lockouts.
        """
        visudo_bin = shutil.which("visudo")
        if not visudo_bin:
            return True, "visudo binary not found; skipped syntax check."

        with tempfile.NamedTemporaryFile("w", delete=False) as tf:
            tf.write(content.strip() + "\n")
            temp_path = tf.name

        try:
            res = subprocess.run(
                [visudo_bin, "-c", "-f", temp_path],
                capture_output=True,
                text=True,
                check=False,
            )
            is_valid = (res.returncode == 0)
            msg = res.stdout if is_valid else (res.stderr or res.stdout)
            return is_valid, msg.strip()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
