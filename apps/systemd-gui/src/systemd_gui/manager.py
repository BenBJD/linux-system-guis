"""Backend wrappers and data models for systemd services and timers."""

from dataclasses import dataclass
import subprocess
from linux_gui_core.runner.executor import SafeExecutor, ExecutionResult


@dataclass
class ServiceUnit:
    name: str
    load: str
    active: str
    sub: str
    description: str
    friendly_status: str = "Stopped"
    friendly_boot: str = "Manual only"


@dataclass
class TimerUnit:
    next_elapse: str
    left: str
    last_trigger: str
    passed: str
    unit: str
    activates: str


class SystemdManager:
    @staticmethod
    def _translate_runtime_status(active: str, sub: str, load: str) -> str:
        """Translates systemd technical active/sub states into human-friendly status strings."""
        if load == "not-found":
            return "Not installed"
        if active == "failed" or sub == "failed":
            return "Crashed / Failed"
        if active == "active" and sub == "running":
            return "Running"
        if active == "active" and sub == "exited":
            return "Completed (one-shot)"
        if active == "active" and sub == "waiting":
            return "Idle / Waiting"
        if active == "inactive" or sub == "dead":
            return "Stopped"
        if active == "activating":
            return "Starting up..."
        if active == "deactivating":
            return "Stopping..."
        return f"⚪ {active} ({sub})"

    @staticmethod
    def _translate_boot_status(enablement: str) -> str:
        """Translates systemd unit file enablement into human-friendly boot startup strings."""
        clean = enablement.lower().strip()
        if "enabled" in clean:
            return "Runs on boot (Enabled)"
        if "disabled" in clean:
            return "Manual start only (Disabled)"
        if "masked" in clean:
            return "Blocked completely (Masked)"
        if "static" in clean:
            return "Dependency only (Starts if needed)"
        if "indirect" in clean:
            return "Managed by another unit"
        return "Unknown / Not found"

    @classmethod
    def get_unit_file_enablement(cls, user_mode: bool = False) -> dict[str, str]:
        """Maps unit file names to their boot enablement state (enabled, disabled, etc.)."""
        cmd = ["systemctl"]
        if user_mode:
            cmd.append("--user")
        cmd.extend(["list-unit-files", "--type=service", "--no-pager", "--no-legend", "--plain"])

        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        mapping = {}
        for line in res.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                mapping[parts[0]] = parts[1]
        return mapping

    @classmethod
    def list_services(cls, user_mode: bool = False) -> list[ServiceUnit]:
        """Fetch list of service units with beginner-friendly state translations."""
        enablement_map = cls.get_unit_file_enablement(user_mode)

        cmd = ["systemctl"]
        if user_mode:
            cmd.append("--user")
        # --plain strips bullet points/dots!
        cmd.extend(["list-units", "--type=service", "--all", "--no-pager", "--no-legend", "--plain"])

        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        units = []
        for line in res.stdout.splitlines():
            clean_line = line.strip()
            # Defensive check: if line starts with bullet symbols (●, *, •), strip them
            while clean_line and clean_line[0] in ("●", "*", "•", "x"):
                clean_line = clean_line[1:].strip()

            parts = clean_line.split(maxsplit=4)
            if len(parts) >= 5:
                name = parts[0]
                load = parts[1]
                active = parts[2]
                sub = parts[3]
                desc = parts[4]

                # If name looks invalid or is just a symbol, skip
                if not name.endswith(".service"):
                    # Check if part 1 had the service name
                    if len(parts) > 1 and parts[1].endswith(".service"):
                        name = parts[1]

                friendly_status = cls._translate_runtime_status(active, sub, load)
                raw_enable = enablement_map.get(name, "not-found" if load == "not-found" else "unknown")
                friendly_boot = cls._translate_boot_status(raw_enable)

                units.append(
                    ServiceUnit(
                        name=name,
                        load=load,
                        active=active,
                        sub=sub,
                        description=desc,
                        friendly_status=friendly_status,
                        friendly_boot=friendly_boot,
                    )
                )
        return units

    @staticmethod
    def list_timers(user_mode: bool = False) -> list[TimerUnit]:
        """Fetch list of active timers."""
        cmd = ["systemctl"]
        if user_mode:
            cmd.append("--user")
        cmd.extend(["list-timers", "--all", "--no-pager", "--no-legend", "--plain"])

        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        timers = []
        for line in res.stdout.splitlines():
            clean_line = line.strip()
            while clean_line and clean_line[0] in ("●", "*", "•"):
                clean_line = clean_line[1:].strip()

            parts = clean_line.split()
            if len(parts) >= 6:
                timers.append(
                    TimerUnit(
                        next_elapse=f"{parts[0]} {parts[1]}",
                        left=parts[2],
                        last_trigger=f"{parts[3]} {parts[4]}",
                        passed=parts[5],
                        unit=parts[-2] if len(parts) > 6 else parts[5],
                        activates=parts[-1],
                    )
                )
        return timers

    @staticmethod
    def get_unit_status(unit_name: str, user_mode: bool = False) -> str:
        # Strip any accidental bullet points or spaces
        clean_name = unit_name.strip("● *• \t\n\r")
        if not clean_name:
            return ""

        cmd = ["systemctl"]
        if user_mode:
            cmd.append("--user")
        cmd.extend(["status", clean_name, "--no-pager"])
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return res.stdout or res.stderr

    @staticmethod
    def build_command_str(action: str, unit: str, user_mode: bool = False) -> str:
        clean_unit = unit.strip("● *• \t\n\r")
        prefix = "systemctl --user" if user_mode else "sudo systemctl"
        return f"{prefix} {action} {clean_unit}"

    @staticmethod
    def execute_unit_action(action: str, unit: str, user_mode: bool = False) -> ExecutionResult:
        clean_unit = unit.strip("● *• \t\n\r")
        cmd = ["systemctl"]
        if user_mode:
            cmd.append("--user")
        cmd.extend(action.split() + ([clean_unit] if clean_unit else []))
        elevated = not user_mode
        return SafeExecutor.run_command(cmd, elevated=elevated)
