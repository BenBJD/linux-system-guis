"""Package manager integration for checking file ownership across Linux distributions."""

from dataclasses import dataclass
import os
import re
import shutil
import subprocess


@dataclass
class PackageOwnership:
    is_managed: bool
    package_name: str | None = None
    package_version: str | None = None
    package_manager: str | None = None
    raw_output: str = ""

    def summary_text(self) -> str:
        if not self.is_managed:
            return "User-created / Unmanaged"
        ver = f" ({self.package_version})" if self.package_version else ""
        return f"Package: {self.package_name}{ver} via {self.package_manager}"


class PackageManagerInspector:
    """Inspects whether system configuration files are owned/managed by a package manager

    such as pacman, dpkg/apt, rpm/dnf, or apk.
    """

    _cache: dict[str, PackageOwnership] = {}

    @classmethod
    def get_available_package_manager(cls) -> str | None:
        """Detect the primary system package manager."""
        for pm in ("pacman", "dpkg", "rpm", "apk"):
            if shutil.which(pm):
                return pm
        return None

    @classmethod
    def check_file_owner(cls, file_path: str) -> PackageOwnership:
        """Check which package owns the specified file path."""
        if not file_path:
            return PackageOwnership(is_managed=False)

        abs_path = os.path.abspath(file_path)
        if abs_path in cls._cache:
            return cls._cache[abs_path]

        pm = cls.get_available_package_manager()
        if not pm or not os.path.exists(abs_path):
            res = PackageOwnership(is_managed=False, package_manager=pm)
            cls._cache[abs_path] = res
            return res

        ownership = PackageOwnership(is_managed=False, package_manager=pm)

        try:
            if pm == "pacman":
                # pacman -Qo /path/to/file
                proc = subprocess.run(
                    ["pacman", "-Qo", abs_path],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if proc.returncode == 0:
                    # Output: "/path/to/file is owned by package-name 1.2.3-4"
                    m = re.search(r"is owned by\s+([^\s]+)(?:\s+([^\s]+))?", proc.stdout)
                    if m:
                        ownership.is_managed = True
                        ownership.package_name = m.group(1)
                        ownership.package_version = m.group(2)
                        ownership.raw_output = proc.stdout.strip()

            elif pm == "dpkg":
                # dpkg -S /path/to/file
                proc = subprocess.run(
                    ["dpkg", "-S", abs_path],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if proc.returncode == 0:
                    # Output: "package-name: /path/to/file"
                    m = re.search(r"^([^:]+):", proc.stdout)
                    if m:
                        ownership.is_managed = True
                        ownership.package_name = m.group(1).strip()
                        ownership.raw_output = proc.stdout.strip()

            elif pm == "rpm":
                # rpm -qf /path/to/file
                proc = subprocess.run(
                    ["rpm", "-qf", abs_path],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if proc.returncode == 0 and not proc.stdout.startswith("file "):
                    ownership.is_managed = True
                    ownership.package_name = proc.stdout.strip()
                    ownership.raw_output = proc.stdout.strip()

            elif pm == "apk":
                # apk info -W /path/to/file
                proc = subprocess.run(
                    ["apk", "info", "-W", abs_path],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if proc.returncode == 0 and "is owned by" in proc.stdout:
                    parts = proc.stdout.split("is owned by")
                    if len(parts) > 1:
                        ownership.is_managed = True
                        ownership.package_name = parts[1].strip()
                        ownership.raw_output = proc.stdout.strip()

        except Exception as e:
            ownership.raw_output = f"Inspection error: {e}"

        cls._cache[abs_path] = ownership
        return ownership
