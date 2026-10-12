"""Backend parsers and regeneration commands for GRUB and systemd-boot."""

from dataclasses import dataclass, field
import glob
import os
import re
import shutil
import subprocess
from linux_gui_core.runner.executor import ExecutionResult, SafeExecutor


@dataclass
class BootloaderConfig:
    bootloader_type: str = "grub"  # "grub" or "systemd-boot"
    timeout: int = 5
    default_entry: str = "0"
    kernel_params: list[str] = field(default_factory=list)
    raw_content: str = ""
    config_file_path: str = "/etc/default/grub"
    # systemd-boot specific attributes
    esp_path: str = "/efi"
    loader_conf_path: str = ""
    cmdline_file_path: str = "/etc/kernel/cmdline"
    detected_details: str = ""
    is_protected: bool = False


COMMON_KERNEL_ARGS = [
    ("quiet", "Suppress non-critical kernel messages during startup for clean boot screen.", "Safe", "quiet"),
    ("splash", "Enable graphical boot animation screen.", "Safe", "splash"),
    ("nomodeset", "Disable kernel mode setting. Troubleshooting parameter for GPU driver crashes or black screens.", "Safe / Troubleshooting", "nomodeset"),
    ("nowatchdog", "Disable hardware watchdog timer drivers to speed up system boot and shutdown.", "Safe / Performance", "nowatchdog"),
    ("loglevel=3", "Set console loglevel to error-only (1=emerg, 3=err, 4=warn, 7=debug).", "Safe", "loglevel=3"),
]


class BootloaderBackend:
    @staticmethod
    def detect_active_bootloader() -> tuple[str, str]:
        """Determines if the running system booted via systemd-boot or GRUB.

        Returns (type_str, detail_description).
        """
        # 1. Check UEFI LoaderInfo efivar
        for efivar_path in glob.glob("/sys/firmware/efi/efivars/LoaderInfo-*"):
            try:
                with open(efivar_path, "rb") as fp:
                    # Skip 4-byte attributes header
                    raw = fp.read()[4:].decode("utf-16-le", errors="ignore").strip().rstrip("\x00")
                    if "systemd-boot" in raw.lower():
                        return "systemd-boot", raw
            except Exception:
                pass

        # 2. Check bootctl status output
        if shutil.which("bootctl"):
            try:
                res = subprocess.run(["bootctl", "status"], capture_output=True, text=True, check=False)
                if "systemd-boot" in res.stdout.lower():
                    # Extract version line if possible
                    m = re.search(r"Product:\s*(systemd-boot[^\n]+)", res.stdout)
                    details = m.group(1).strip() if m else "systemd-boot"
                    return "systemd-boot", details
            except Exception:
                pass

        # 3. Check for EFI loader directories
        for cand in ("/efi/loader", "/boot/loader"):
            if os.path.isdir(cand):
                return "systemd-boot", f"systemd-boot ({cand})"

        # 4. Check for GRUB
        if os.path.exists("/boot/grub/grub.cfg") or os.path.exists("/etc/default/grub"):
            return "grub", "GRUB 2 (/etc/default/grub)"

        return "grub", "GRUB (Default)"

    @staticmethod
    def detect_esp_path() -> str:
        """Find the EFI System Partition mount point."""
        candidates = ["/efi", "/boot", "/boot/efi"]
        for c in candidates:
            if os.path.exists(os.path.join(c, "loader")) or os.path.exists(os.path.join(c, "EFI")):
                return c
        return "/efi" if os.path.exists("/efi") else "/boot"

    @staticmethod
    def load_grub_config(path: str = "/etc/default/grub") -> BootloaderConfig:
        cfg = BootloaderConfig(
            bootloader_type="grub",
            config_file_path=path,
            detected_details="GRUB 2",
        )
        if not os.path.exists(path):
            return cfg

        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg.raw_content = f.read()
        except PermissionError:
            res = SafeExecutor.run_command(["cat", path], elevated=True)
            cfg.raw_content = res.stdout

        for line in cfg.raw_content.splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k == "GRUB_TIMEOUT":
                try:
                    cfg.timeout = int(v)
                except ValueError:
                    pass
            elif k == "GRUB_DEFAULT":
                cfg.default_entry = v
            elif k == "GRUB_CMDLINE_LINUX_DEFAULT":
                cfg.kernel_params = v.split()
        return cfg

    @staticmethod
    def load_systemd_boot_config() -> BootloaderConfig:
        """Loads configuration and kernel parameters for systemd-boot."""
        esp = BootloaderBackend.detect_esp_path()
        loader_conf = os.path.join(esp, "loader", "loader.conf")
        cmdline_file = "/etc/kernel/cmdline"

        cfg = BootloaderConfig(
            bootloader_type="systemd-boot",
            config_file_path=loader_conf,
            esp_path=esp,
            loader_conf_path=loader_conf,
            cmdline_file_path=cmdline_file,
            timeout=5,
            default_entry="@saved",
        )

        # 1. Read LoaderEntrySelected efivar if available for active entry
        for efivar in glob.glob("/sys/firmware/efi/efivars/LoaderEntrySelected-*"):
            try:
                with open(efivar, "rb") as fp:
                    entry = fp.read()[4:].decode("utf-16-le", errors="ignore").strip().rstrip("\x00")
                    if entry:
                        cfg.default_entry = entry
            except Exception:
                pass

        # 2. Read loader.conf (timeout and default entry)
        if os.path.exists(loader_conf):
            try:
                with open(loader_conf, "r", encoding="utf-8") as f:
                    cfg.raw_content = f.read()
            except PermissionError:
                cfg.is_protected = True
                cfg.raw_content = ""
        else:
            cfg.is_protected = True

        for line in cfg.raw_content.splitlines():
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) >= 2:
                k, v = parts[0].lower(), parts[1].strip()
                if k == "timeout":
                    try:
                        cfg.timeout = int(v)
                    except ValueError:
                        pass
                elif k == "default":
                    cfg.default_entry = v

        # 3. Read kernel parameters from /etc/kernel/cmdline, or fallback to /proc/cmdline
        params: list[str] = []
        if os.path.exists(cmdline_file):
            try:
                with open(cmdline_file, "r", encoding="utf-8") as f:
                    params = f.read().strip().split()
            except Exception:
                pass

        if not params and os.path.exists("/proc/cmdline"):
            try:
                with open("/proc/cmdline", "r", encoding="utf-8") as f:
                    raw_cmdline = f.read().strip().split()
                    # Filter out initrd spec if present
                    params = [p for p in raw_cmdline if not p.startswith("initrd=")]
            except Exception:
                pass

        cfg.kernel_params = params
        return cfg

    @staticmethod
    def serialize_grub_config(cfg: BootloaderConfig) -> str:
        param_str = " ".join(cfg.kernel_params)
        lines = []
        found_timeout = False
        found_default = False
        found_params = False

        for line in cfg.raw_content.splitlines():
            stripped = line.strip()
            if stripped.startswith("GRUB_TIMEOUT="):
                lines.append(f"GRUB_TIMEOUT={cfg.timeout}")
                found_timeout = True
            elif stripped.startswith("GRUB_DEFAULT="):
                lines.append(f'GRUB_DEFAULT="{cfg.default_entry}"')
                found_default = True
            elif stripped.startswith("GRUB_CMDLINE_LINUX_DEFAULT="):
                lines.append(f'GRUB_CMDLINE_LINUX_DEFAULT="{param_str}"')
                found_params = True
            else:
                lines.append(line)

        if not found_timeout:
            lines.append(f"GRUB_TIMEOUT={cfg.timeout}")
        if not found_default:
            lines.append(f'GRUB_DEFAULT="{cfg.default_entry}"')
        if not found_params:
            lines.append(f'GRUB_CMDLINE_LINUX_DEFAULT="{param_str}"')

        return "\n".join(lines) + "\n"

    @staticmethod
    def serialize_systemd_boot_config(cfg: BootloaderConfig) -> tuple[str, str]:
        """Serializes loader.conf content, /etc/kernel/cmdline content."""
        # 1. loader.conf
        lines = []
        found_timeout = False
        found_default = False

        for line in cfg.raw_content.splitlines():
            stripped = line.strip()
            if stripped.startswith("timeout"):
                lines.append(f"timeout {cfg.timeout}")
                found_timeout = True
            elif stripped.startswith("default"):
                lines.append(f"default {cfg.default_entry}")
                found_default = True
            else:
                lines.append(line)

        if not found_default:
            lines.append(f"default {cfg.default_entry}")
        if not found_timeout:
            lines.append(f"timeout {cfg.timeout}")

        loader_conf_text = "\n".join(lines).strip() + "\n"

        # 2. /etc/kernel/cmdline
        cmdline_text = " ".join(cfg.kernel_params).strip() + "\n"
        return loader_conf_text, cmdline_text

    @staticmethod
    def get_grub_regen_command() -> str:
        if shutil.which("update-grub"):
            return "update-grub"
        return "grub-mkconfig -o /boot/grub/grub.cfg"

    @staticmethod
    def get_systemd_boot_regen_command() -> str:
        if shutil.which("reinstall-kernels"):
            return "reinstall-kernels"
        if shutil.which("kernel-install"):
            return "bootctl update"
        return "bootctl update"

    @staticmethod
    def regenerate_bootloader(bootloader_type: str) -> ExecutionResult:
        if bootloader_type == "grub":
            cmd = BootloaderBackend.get_grub_regen_command()
            return SafeExecutor.run_command(cmd.split(), elevated=True)
        else:
            cmd = BootloaderBackend.get_systemd_boot_regen_command()
            return SafeExecutor.run_command(cmd.split(), elevated=True)
